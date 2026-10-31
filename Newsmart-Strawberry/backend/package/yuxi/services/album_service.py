"""Validated, immutable originals with authenticated access through the album API."""

import asyncio
import hashlib
import io
import os
import tempfile
import warnings
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_STORED, ZipFile

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.JpegImagePlugin import JpegImageFile
from PIL.PngImagePlugin import PngImageFile
from PIL.WebPImagePlugin import WebPImageFile
from sqlalchemy.exc import IntegrityError

from yuxi.repositories.album_repository import album_repository

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000


def storage_root():
    return Path(os.getenv("ALBUM_STORAGE_DIR", "saves/albums")).resolve()


def prepare_image(data):
    try:
        # Use explicit supported codecs; Ultralytics patches Image.open to auto-install HEIF on failures.
        decoder = (
            JpegImageFile
            if data.startswith(b"\xff\xd8\xff")
            else PngImageFile
            if data.startswith(b"\x89PNG\r\n\x1a\n")
            else WebPImageFile
            if data.startswith(b"RIFF") and data[8:12] == b"WEBP"
            else None
        )
        if decoder is None:
            raise ValueError("仅支持静态 JPEG、PNG、WebP 图片")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with decoder(io.BytesIO(data)) as image:
                extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(image.format)
                if not extension or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("仅支持静态 JPEG、PNG、WebP 图片")
                width, height = image.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise ValueError("图片像素不得超过 2400 万")
                image.load()
                preview = ImageOps.exif_transpose(image).convert("RGB")
                preview.thumbnail((640, 640))
                output = io.BytesIO()
                preview.save(output, "JPEG", quality=85)
                return extension, width, height, output.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError("图片损坏或无法安全解码") from exc


async def require_album(album_id, user):
    album = await album_repository.get(album_id, user.department_id)
    if album is None:
        raise HTTPException(404, "照片集不存在或无权访问")
    return album


async def create_album(data, user):
    try:
        return await album_repository.create(
            id=uuid4().hex, department_id=user.department_id, owner_uid=str(user.uid), **data
        )
    except IntegrityError as exc:
        raise HTTPException(409, "该草莓簇编号已存在，请使用已有照片集") from exc


async def upload_photo(album_id, upload, captured_at, user, source="upload"):
    await require_album(album_id, user)
    captured_at = captured_at or datetime.now(UTC)
    if captured_at.tzinfo is None:
        raise HTTPException(422, "采集时间必须包含时区")
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "图片不得超过 20 MB")
    try:
        extension, width, height, preview = await asyncio.to_thread(prepare_image, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    photo_id = uuid4().hex
    directory = storage_root() / album_id
    original = directory / f"{photo_id}.{extension}"
    thumbnail = directory / f"{photo_id}.thumb.jpg"
    filename = Path((upload.filename or "image").replace("\\", "/")).name
    filename = "".join(c for c in filename if ord(c) >= 32)[:240] or f"image.{extension}"
    try:
        await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(original.write_bytes, data)
        await asyncio.to_thread(thumbnail.write_bytes, preview)
        return await album_repository.add_photo(
            id=photo_id,
            album_id=album_id,
            department_id=user.department_id,
            owner_uid=str(user.uid),
            filename=filename,
            extension=extension,
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            width=width,
            height=height,
            captured_at=captured_at,
            source=source,
        )
    except BaseException as exc:
        original.unlink(missing_ok=True)
        thumbnail.unlink(missing_ok=True)
        if isinstance(exc, IntegrityError):
            raise HTTPException(409, "该图片已归档到本部门照片集，请勿重复分配") from exc
        raise


async def photo_file(photo_id, user, thumbnail=False):
    photo = await album_repository.photo(photo_id, user.department_id)
    if photo is None:
        raise HTTPException(404, "图片不存在或无权访问")
    suffix = "thumb.jpg" if thumbnail else photo["extension"]
    path = storage_root() / photo["album_id"] / f"{photo['id']}.{suffix}"
    if not path.is_file():
        raise HTTPException(410, "图片文件丢失，请检查存储或恢复备份")
    return path, photo


def build_archive(photos):
    # Originals are already compressed; write to disk without loading the album into memory.
    with tempfile.NamedTemporaryFile(prefix="strawberry-album-", suffix=".zip", delete=False) as file:
        path = Path(file.name)
    try:
        with ZipFile(path, "w", compression=ZIP_STORED) as archive:
            for index, photo in enumerate(photos, 1):
                original = storage_root() / photo["album_id"] / f"{photo['id']}.{photo['extension']}"
                if not original.is_file():
                    raise HTTPException(410, "部分原图文件丢失，请恢复备份后重新下载")
                name = Path(photo["filename"].replace("\\", "/")).name
                name = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name)
                archive.write(original, f"{index:06d}_{name[:180]}")
        return path
    except BaseException:
        path.unlink(missing_ok=True)
        raise


async def album_archive(album_id, user):
    await require_album(album_id, user)
    photos = await album_repository.photos(album_id, user.department_id, limit=None)
    if not photos["items"]:
        raise HTTPException(400, "照片集暂无图片")
    return await asyncio.to_thread(build_archive, photos["items"])
