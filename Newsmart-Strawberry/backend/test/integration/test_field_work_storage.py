"""Real PostgreSQL and ASGI API, no physical camera or actuator access."""

import asyncio
import hashlib
import importlib.util
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
from fastapi import FastAPI, UploadFile
from PIL import Image
from sqlalchemy import delete


def test_shared_backup_models_and_traceability(monkeypatch, tmp_path):
    from server.utils.auth_middleware import get_required_user
    from yuxi.repositories.album_repository import AlbumPhoto, ClusterAlbum, album_repository
    from yuxi.repositories.field_work_repository import FieldRecord, field_repository
    from yuxi.repositories.sensor_history_repository import SensorSample, sensor_history_repository
    from yuxi.services.album_service import create_album, upload_photo
    from yuxi.storage.postgres.manager import pg_manager

    path = Path(__file__).resolve().parents[2] / "server/routers/field_work_router.py"
    spec = importlib.util.spec_from_file_location("field_test_router", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("FIELD_WORK_DIR", str(tmp_path / "work"))
    monkeypatch.setenv("ALBUM_STORAGE_DIR", str(tmp_path / "albums"))
    user = SimpleNamespace(uid="field-test-" + uuid4().hex, role="admin", department_id=193847202)
    owner = user.uid
    app = FastAPI()
    app.include_router(module.field_work)
    app.dependency_overrides[get_required_user] = lambda: user

    async def run():
        pg_manager.initialize()
        await album_repository.initialize()
        await sensor_history_repository.initialize()
        await field_repository.initialize()
        await field_repository.initialize(validate=True)
        try:
            album = await create_album(
                {"cluster_code": uuid4().hex, "name": "Test", "plot": "A", "device_id": owner}, user
            )
            output = io.BytesIO()
            Image.new("RGB", (20, 30), "red").save(output, "PNG")
            photo = await upload_photo(
                album["id"], UploadFile(io.BytesIO(output.getvalue()), filename="fruit.png"), None, user
            )
            await sensor_history_repository.append(
                device_id=owner, kind="air", sampled_at=datetime.now(UTC), values={"temp": 22}
            )
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                uploaded = await client.post(
                    "/field-work/shared", files={"file": ("../../labels.zip", b"labels")}, data={"folder": "training"}
                )
                assert uploaded.status_code == 200, uploaded.text
                shared = uploaded.json()
                assert shared["name"] == "labels.zip"
                assert shared["data"]["sha256"] == hashlib.sha256(b"labels").hexdigest()
                user.uid, user.role = owner + "-colleague", "user"
                assert (await client.get(f"/field-work/files/{shared['id']}")).content == b"labels"
                assert (await client.delete(f"/field-work/shared/{shared['id']}")).status_code == 403
                user.department_id += 1
                assert (await client.get(f"/field-work/files/{shared['id']}")).status_code == 404
                user.department_id -= 1
                user.uid, user.role = owner, "admin"
                assert (
                    await client.post("/field-work/shared", files={"file": ("x", b"x")}, data={"folder": "../escape"})
                ).status_code == 422
                backup = await client.post(
                    "/field-work/backups",
                    json={
                        "album_id": album["id"],
                        "start": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
                        "end": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                    },
                )
                assert backup.status_code == 200, backup.text
                result = backup.json()
                assert result["data"]["photos"] == 1 and result["data"]["sensor_rows"] == 1
                archive = (await client.get(f"/field-work/files/{result['id']}")).content
                assert hashlib.sha256(archive).hexdigest() == result["data"]["sha256"]
                with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                    manifest = json.loads(zipped.read("manifest.json"))
                    for item in manifest["files"]:
                        assert hashlib.sha256(zipped.read(item["path"])).hexdigest() == item["sha256"]
                missing = await client.post("/field-work/detections", json={"photo_id": photo["id"], "task": "disease"})
                assert missing.status_code == 409
                invalid = await client.post(
                    "/field-work/models",
                    data={"task": "maturity", "trusted": "false"},
                    files={"file": ("x.pt", b"invalid")},
                )
                assert invalid.status_code == 422
                analysis = await client.post("/field-work/analyses", json={"album_id": album["id"]})
                assert analysis.status_code == 200, analysis.text
                assert analysis.json()["data"]["estimate"]["status"] == "insufficient_data"
                weights = Path(__file__).resolve().parents[2] / "package/yuxi/detect/models/best.pt"
                model = await client.post(
                    "/field-work/models",
                    data={"task": "maturity", "trusted": "true"},
                    files={"file": ("trusted-project-fixture.pt", weights.read_bytes())},
                )
                assert model.status_code == 200, model.text
                version = model.json()
                assert version["status"] == "validated"
                assert (await client.post(f"/field-work/models/{version['id']}/activate")).status_code == 200
                detected = await client.post(
                    "/field-work/detections", json={"photo_id": photo["id"], "task": "maturity"}
                )
                assert detected.status_code == 200, detected.text
                assert detected.json()["data"]["model_id"] == version["id"]
                assert (await client.delete(f"/field-work/photos/{photo['id']}")).status_code == 409
                model_path = tmp_path / "work" / f"{version['id']}.pt"
                with model_path.open("ab") as stream:
                    stream.write(b"tamper")
                assert (await client.post(f"/field-work/models/{version['id']}/activate")).status_code == 422
                failed = await client.post("/field-work/detections", json={"photo_id": photo["id"], "task": "maturity"})
                assert failed.status_code == 422
                evidence = (await client.get("/field-work/records/detection")).json()
                assert any(record["status"] == "failed" for record in evidence)
                clean_image = io.BytesIO()
                Image.new("RGB", (10, 10), "blue").save(clean_image, "PNG")
                removable = await upload_photo(
                    album["id"], UploadFile(io.BytesIO(clean_image.getvalue()), filename="unused.png"), None, user
                )
                assert (await client.delete(f"/field-work/photos/{removable['id']}")).status_code == 200
                capture = await client.post("/field-work/captures", json={"album_id": album["id"], "camera_id": 0})
                assert capture.json()["status"] == "paused"
                await field_repository.change(capture.json()["id"], user.department_id, status="running")
                await field_repository.recover()
                assert (await field_repository.get(capture.json()["id"], user.department_id))["status"] == "paused"
                assert (await client.delete(f"/field-work/shared/{shared['id']}")).status_code == 200
                assert (await client.get(f"/field-work/files/{shared['id']}")).status_code == 404
        finally:
            async with pg_manager.get_async_session_context() as session:
                await session.execute(delete(FieldRecord).where(FieldRecord.owner_uid == owner))
                await session.execute(delete(AlbumPhoto).where(AlbumPhoto.owner_uid == owner))
                await session.execute(delete(ClusterAlbum).where(ClusterAlbum.owner_uid == owner))
                await session.execute(delete(SensorSample).where(SensorSample.device_id == owner))
            await pg_manager.close()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(run())
