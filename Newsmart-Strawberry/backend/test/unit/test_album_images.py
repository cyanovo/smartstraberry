import io
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zipfile import ZipFile

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from yuxi.services import album_service as service


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (80, 60), "red").save(output, "PNG")
    return output.getvalue()


def test_image_decode_and_thumbnail():
    extension, width, height, preview = service.prepare_image(image_bytes())
    assert (extension, width, height) == ("png", 80, 60)
    assert Image.open(io.BytesIO(preview)).format == "JPEG"
    with pytest.raises(ValueError):
        service.prepare_image(b"not an image")


async def test_failed_database_write_removes_original_and_thumbnail(monkeypatch, tmp_path):
    monkeypatch.setenv("ALBUM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(service.album_repository, "get", AsyncMock(return_value={"id": "a"}))
    monkeypatch.setattr(service.album_repository, "add_photo", AsyncMock(side_effect=RuntimeError("db failed")))
    with pytest.raises(RuntimeError, match="db failed"):
        await service.upload_photo(
            "a",
            UploadFile(io.BytesIO(image_bytes()), filename="a.png"),
            None,
            SimpleNamespace(uid="u", department_id=1),
        )
    assert not list(tmp_path.rglob("*.png"))
    assert not list(tmp_path.rglob("*.jpg"))


async def test_forbidden_album_is_checked_before_file_read(monkeypatch):
    monkeypatch.setattr(service.album_repository, "get", AsyncMock(return_value=None))
    upload = AsyncMock()
    with pytest.raises(HTTPException) as caught:
        await service.upload_photo("other", upload, None, SimpleNamespace(department_id=1))
    assert caught.value.status_code == 404
    upload.read.assert_not_awaited()


async def test_oversize_image_is_rejected(monkeypatch):
    monkeypatch.setattr(service.album_repository, "get", AsyncMock(return_value={"id": "a"}))
    monkeypatch.setattr(service, "MAX_IMAGE_BYTES", 2)
    with pytest.raises(HTTPException) as caught:
        await service.upload_photo("a", UploadFile(io.BytesIO(b"123")), None, SimpleNamespace(department_id=1))
    assert caught.value.status_code == 413


async def test_archive_contains_all_originals_with_unique_safe_names(monkeypatch, tmp_path):
    monkeypatch.setenv("ALBUM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(service.album_repository, "get", AsyncMock(return_value={"id": "a"}))
    photos = [{"id": str(i), "album_id": "a", "filename": "../草莓.png", "extension": "png"} for i in range(35)]
    listing = AsyncMock(return_value={"items": photos, "total": 35})
    monkeypatch.setattr(service.album_repository, "photos", listing)
    (tmp_path / "a").mkdir()
    original = image_bytes()
    for photo in photos:
        (tmp_path / "a" / f"{photo['id']}.png").write_bytes(original)
    path = await service.album_archive("a", SimpleNamespace(department_id=7))
    try:
        listing.assert_awaited_once_with("a", 7, limit=None)
        with ZipFile(path) as archive:
            assert len(set(archive.namelist())) == 35
            assert all("/" not in name and ".." not in name for name in archive.namelist())
            assert all(archive.read(name) == original for name in archive.namelist())
    finally:
        path.unlink()


async def test_archive_checks_access_and_empty_album(monkeypatch):
    listing = AsyncMock(return_value={"items": [], "total": 0})
    monkeypatch.setattr(service.album_repository, "photos", listing)
    monkeypatch.setattr(service.album_repository, "get", AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as caught:
        await service.album_archive("a", SimpleNamespace(department_id=7))
    assert caught.value.status_code == 404
    listing.assert_not_awaited()
    monkeypatch.setattr(service.album_repository, "get", AsyncMock(return_value={"id": "a"}))
    with pytest.raises(HTTPException) as caught:
        await service.album_archive("a", SimpleNamespace(department_id=7))
    assert caught.value.status_code == 400


def test_archive_missing_original_cleans_temporary_zip(monkeypatch, tmp_path):
    monkeypatch.setenv("ALBUM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(service.tempfile, "tempdir", str(tmp_path))
    with pytest.raises(HTTPException) as caught:
        service.build_archive([{"album_id": "a", "id": "missing", "extension": "png", "filename": "a.png"}])
    assert caught.value.status_code == 410
    assert not list(tmp_path.glob("*.zip"))
