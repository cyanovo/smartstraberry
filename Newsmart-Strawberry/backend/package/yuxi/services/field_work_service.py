"""Native Windows capture, team exchange and verifiable backup workflows."""

import asyncio
import hashlib
import io
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile

from yuxi.repositories.album_repository import album_repository
from yuxi.repositories.field_work_repository import field_repository as repo
from yuxi.repositories.sensor_history_repository import sensor_history_repository
from yuxi.services.album_service import photo_file, require_album, upload_photo
from yuxi.services.sensor_history_service import EXPORT_LIMIT, history_csv, validate_range


def work_root():
    root = Path(os.getenv("FIELD_WORK_DIR", "saves/field-work")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


async def require_record(record_id, user, kind=None):
    row = await repo.get(record_id, user.department_id, kind)
    if not row or row["status"] == "deleted":
        raise HTTPException(404, "记录不存在或无权访问")
    return row


def require_manager(user, row=None):
    if user.role not in ("admin", "superadmin") and (row is None or row["owner_uid"] != str(user.uid)):
        raise HTTPException(403, "仅上传者或管理员可执行此操作")


def folder_name(value):
    value = value.replace("\\", "/").strip("/")
    path = PurePosixPath(value)
    if any(part in (".", "..") or ":" in part for part in value.split("/")) or len(value) > 128:
        raise HTTPException(422, "目录名称无效")
    return str(path) if value else ""


async def shared_upload(upload, folder, user, version_note=""):
    folder = folder_name(folder)
    filename = Path((upload.filename or "file").replace("\\", "/")).name[:240]
    data = await upload.read(100 * 1024 * 1024 + 1)
    if not data or len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "文件不能为空且不得超过 100 MB")
    row = await repo.create(
        "shared",
        filename,
        user,
        parent_id=folder,
        status="uploading",
        data={"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "version_note": version_note},
    )
    path = work_root() / row["id"]
    try:
        await asyncio.to_thread(path.write_bytes, data)
        await repo.change(row["id"], user.department_id, status="ready")
    except BaseException:
        path.unlink(missing_ok=True)
        await repo.change(row["id"], user.department_id, status="failed")
        raise
    return await require_record(row["id"], user)


async def download_record(record_id, user):
    row = await require_record(record_id, user)
    if row["kind"] not in ("shared", "backup") or row["status"] != "ready":
        raise HTTPException(409, "文件尚未就绪")
    path = work_root() / row["id"]
    if not path.is_file():
        raise HTTPException(410, "文件丢失")
    return path, row


async def delete_shared(record_id, user):
    row = await require_record(record_id, user, "shared")
    require_manager(user, row)
    await repo.change(record_id, user.department_id, status="deleted")
    (work_root() / record_id).unlink(missing_ok=True)


async def create_backup(album_id, start, end, user):
    validate_range(start, end)
    album = await require_album(album_id, user)
    if not album["device_id"]:
        raise HTTPException(422, "照片集必须先绑定传感器设备编号")
    row = await repo.create(
        "backup",
        f"{album['cluster_code']}-backup.zip",
        user,
        parent_id=album_id,
        status="running",
        data={"start": start.isoformat(), "end": end.isoformat()},
    )
    path = work_root() / row["id"]
    try:
        sensors = await sensor_history_repository.query(
            device_id=album["device_id"], start=start, end=end, limit=EXPORT_LIMIT
        )
        if sensors["total"] > EXPORT_LIMIT:
            raise HTTPException(413, "日志超过 50000 条，请缩小时间范围")
        photos = await album_repository.photos(album_id, user.department_id, limit=10001)
        if photos["total"] > 10000:
            raise HTTPException(413, "照片集超过单次备份上限")
        selected = [p for p in photos["items"] if start <= datetime.fromisoformat(p["captured_at"]) <= end]
        if sum(p["size"] for p in selected) > 2 * 1024**3:
            raise HTTPException(413, "单次备份原图不得超过 2 GB")
        entries = []
        for photo in selected:
            original, _ = await photo_file(photo["id"], user)
            entries.append((original, f"photos/{photo['id']}.{photo['extension']}", photo))
        csv_data = history_csv(sensors["items"])

        def pack():
            manifest = {"album": album, "start": start.isoformat(), "end": end.isoformat(), "files": []}
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for original, name, photo in entries:
                    content = original.read_bytes()
                    digest = hashlib.sha256(content).hexdigest()
                    if digest != photo["sha256"]:
                        raise ValueError(f"原图校验失败: {photo['id']}")
                    archive.writestr(name, content)
                    manifest["files"].append({"path": name, "sha256": digest, "photo": photo})
                archive.writestr("sensors.csv", csv_data)
                manifest["files"].append({"path": "sensors.csv", "sha256": hashlib.sha256(csv_data).hexdigest()})
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            return {
                **row["data"],
                "sha256": digest,
                "size": path.stat().st_size,
                "photos": len(entries),
                "sensor_rows": sensors["total"],
            }

        data = await asyncio.to_thread(pack)
        await repo.change(row["id"], user.department_id, status="ready", data=data)
    except Exception as exc:
        path.unlink(missing_ok=True)
        await repo.change(row["id"], user.department_id, status="failed", data={**row["data"], "error": str(exc)[:500]})
        raise
    return await require_record(row["id"], user)


class CaptureService:
    def __init__(self):
        self.tasks = {}
        self.users = {}
        self.lifecycle_lock = asyncio.Lock()
        self.camera_lock = asyncio.Lock()

    async def start(self, record_id, user):
        row = await require_record(record_id, user, "capture")
        require_manager(user, row)
        async with self.lifecycle_lock:
            if record_id in self.tasks:
                return row
            await repo.change(record_id, user.department_id, status="running")
            self.users[record_id] = user
            self.tasks[record_id] = asyncio.create_task(self.run(row, user))
        return await require_record(record_id, user)

    async def stop(self, record_id, user):
        row = await require_record(record_id, user, "capture")
        require_manager(user, row)
        async with self.lifecycle_lock:
            await repo.change(record_id, user.department_id, status="paused")
            task = self.tasks.get(record_id)
            if task:
                # A capture already in progress finishes saving before stop returns.
                await task
        return await require_record(record_id, user)

    async def run(self, row, user):
        from yuxi.detect.camera import camera_manager
        import cv2

        try:
            while (await require_record(row["id"], user))["status"] == "running":
                async with self.camera_lock:
                    frame = await asyncio.to_thread(camera_manager.capture, row["data"]["camera_id"])
                if frame is None:
                    raise RuntimeError("摄像头未返回画面")
                ok, encoded = await asyncio.to_thread(cv2.imencode, ".jpg", frame)
                if not ok:
                    raise RuntimeError("照片编码失败")
                photo = await upload_photo(
                    row["parent_id"],
                    UploadFile(io.BytesIO(encoded.tobytes()), filename="capture.jpg"),
                    datetime.now(UTC),
                    user,
                    source=row["id"],
                )
                current = await require_record(row["id"], user)
                await repo.change(
                    row["id"],
                    user.department_id,
                    status=current["status"],
                    data={**current["data"], "last_photo_id": photo["id"], "last_capture": photo["captured_at"]},
                    expected=current["status"],
                )
                for _ in range(row["data"]["interval_seconds"]):
                    await asyncio.sleep(1)
                    if (await require_record(row["id"], user))["status"] != "running":
                        return
        except Exception as exc:
            current = await require_record(row["id"], user)
            await repo.change(
                row["id"], user.department_id, status="failed", data={**current["data"], "error": str(exc)[:500]}
            )
        finally:
            self.tasks.pop(row["id"], None)
            self.users.pop(row["id"], None)

    async def shutdown(self):
        for record_id in list(self.tasks):
            await repo.change(record_id, self.users[record_id].department_id, status="paused")
        await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)


capture_service = CaptureService()
