"""Isolated ASGI routes with real PostgreSQL and temporary original-image storage."""

import asyncio
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import delete


def test_album_upload_permissions_and_storage(monkeypatch, tmp_path):
    from server.utils.auth_middleware import get_db, get_required_user
    from yuxi.repositories.album_repository import AlbumPhoto, ClusterAlbum, album_repository
    from yuxi.storage.postgres.manager import pg_manager

    path = Path(__file__).resolve().parents[2] / "server/routers/album_router.py"
    spec = importlib.util.spec_from_file_location("album_test_router", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("ALBUM_STORAGE_DIR", str(tmp_path))
    uid = "album-test-" + uuid4().hex
    user = SimpleNamespace(uid=uid, department_id=193847201)
    app = FastAPI()
    app.include_router(module.albums)
    app.dependency_overrides[get_required_user] = lambda: user

    async def empty_db():
        yield None

    app.dependency_overrides[get_db] = empty_db

    async def run():
        pg_manager.initialize()
        await album_repository.initialize()
        await album_repository.initialize(validate=True)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                body = {"cluster_code": uuid4().hex, "name": "草莓一号", "plot": "A", "device_id": "strawberry-local"}
                response = await client.post("/albums", json=body)
                assert response.status_code == 201, response.text
                album = response.json()
                assert (await client.post("/albums", json=body)).status_code == 409
                assert (await client.post("/albums", json={**body, "cluster_code": "../bad"})).status_code == 422
                output = io.BytesIO()
                Image.new("RGB", (80, 60), "green").save(output, "PNG")
                image = output.getvalue()
                url = f"/albums/{album['id']}/photos"
                uploaded = await client.post(url, files={"file": ("../../sample.png", image, "image/png")})
                assert uploaded.status_code == 201, uploaded.text
                photo = uploaded.json()
                assert photo["filename"] == "sample.png"
                assert (await client.post(url, files={"file": ("x.png", image)})).status_code == 409
                second = await client.post("/albums", json={**body, "cluster_code": uuid4().hex})
                second_url = f"/albums/{second.json()['id']}/photos"
                assert (await client.post(second_url, files={"file": ("x.png", image)})).status_code == 409
                assert (await client.get(second_url)).json()["total"] == 0
                assert len(list(tmp_path.rglob("*.png"))) == 1
                assert (await client.post(url, files={"file": ("x.png", b"broken")})).status_code == 422
                assert (await client.get(url)).json()["total"] == 1
                assert (await client.get(url + "?offset=1")).json()["items"] == []
                file_url = f"/albums/photos/{photo['id']}/file"
                original = await client.get(file_url)
                assert original.content == image
                assert original.headers["cache-control"] == "private, no-store"
                assert Image.open(io.BytesIO((await client.get(file_url + "?thumbnail=true")).content)).format == "JPEG"
                user.uid = uid + "-colleague"
                assert (await client.get(url)).status_code == 200
                user.department_id += 1
                assert (await client.get(url)).status_code == 404
                assert (await client.get(file_url)).status_code == 404
                assert (await client.get("/albums")).json()["items"] == []
                user.department_id -= 1
                (tmp_path / album["id"] / f"{photo['id']}.png").unlink()
                assert (await client.get(file_url)).status_code == 410
                app.dependency_overrides.pop(get_required_user)
                assert (await client.get("/albums")).status_code == 401
        finally:
            async with pg_manager.get_async_session_context() as session:
                await session.execute(delete(AlbumPhoto).where(AlbumPhoto.owner_uid == uid))
                await session.execute(delete(ClusterAlbum).where(ClusterAlbum.owner_uid == uid))
            await pg_manager.close()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(run())
