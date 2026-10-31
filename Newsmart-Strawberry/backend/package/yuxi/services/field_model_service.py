"""Trusted model versions and immutable image/model inference provenance."""

import asyncio
import hashlib
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps
from sqlalchemy import select, text

from yuxi.repositories.field_work_repository import FieldRecord, field_repository as repo
from yuxi.services.album_service import photo_file
from yuxi.services.field_work_service import require_manager, require_record, work_root
from yuxi.storage.postgres.manager import pg_manager

model_lock = asyncio.Lock()


def validate_classes(names, task):
    values = [str(value) for value in names.values()] if isinstance(names, dict) else list(names)
    if not values or len(values) > 200:
        raise ValueError("模型类别为空或超过 200 类")
    if task == "maturity":
        normalized = {name.lower().replace("_", "-").replace(" ", "-") for name in values}
        if normalized != {"unripe", "half-ripe", "ripe"}:
            raise ValueError("成熟度模型类别必须为 Unripe、Half-ripe、Ripe")
    return values


def load_and_test(path, task):
    import numpy as np
    from ultralytics import YOLO

    model = YOLO(str(path), task="detect")
    if model.task != "detect":
        raise ValueError("仅支持目标检测模型")
    names = validate_classes(model.names, task)
    model.predict(np.zeros((320, 320, 3), dtype=np.uint8), device="cpu", verbose=False)
    return names


async def upload_model(upload, task, trusted, user):
    require_manager(user)
    if not trusted:
        raise HTTPException(422, "必须确认模型来自可信训练环境；PT 文件可能执行代码")
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in (".pt", ".onnx"):
        raise HTTPException(422, "仅支持可信的 YOLO PT 或 ONNX 检测模型")
    content = await upload.read(200 * 1024**2 + 1)
    if not content or len(content) > 200 * 1024**2:
        raise HTTPException(413, "模型不得为空或超过 200 MB")
    row = await repo.create(
        "model",
        Path(upload.filename.replace("\\", "/")).name[:240],
        user,
        parent_id=task,
        status="validating",
        data={
            "task": task,
            "extension": suffix,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
            "trusted": True,
        },
    )
    path = work_root() / f"{row['id']}{suffix}"
    try:
        await asyncio.to_thread(path.write_bytes, content)
        async with model_lock:
            names = await asyncio.to_thread(load_and_test, path, task)
        await repo.change(row["id"], user.department_id, status="validated", data={**row["data"], "classes": names})
    except Exception as exc:
        await repo.change(row["id"], user.department_id, status="failed", data={**row["data"], "error": str(exc)[:500]})
        raise HTTPException(422, f"模型加载测试失败: {str(exc)[:300]}") from exc
    return await require_record(row["id"], user)


async def activate_model(record_id, user):
    require_manager(user)
    row = await require_record(record_id, user, "model")
    if row["status"] not in ("validated", "active", "inactive"):
        raise HTTPException(409, "仅可启用通过加载测试的模型")
    path = work_root() / f"{row['id']}{row['data']['extension']}"
    async with model_lock:
        try:
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != row["data"]["sha256"]:
                    raise ValueError("模型文件校验失败")
            await asyncio.to_thread(load_and_test, path, row["parent_id"])
        except Exception as exc:
            raise HTTPException(422, f"模型启用失败，原版本保持不变: {str(exc)[:200]}") from exc
        async with pg_manager.get_async_session_context() as session:
            # Serialize activation across processes, not just requests in one API worker.
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": f"field-model:{user.department_id}:{row['parent_id']}"},
            )
            models = await session.scalars(
                select(FieldRecord).where(
                    FieldRecord.kind == "model",
                    FieldRecord.department_id == user.department_id,
                    FieldRecord.parent_id == row["parent_id"],
                )
            )
            for model in models:
                if model.id == record_id:
                    model.status = "active"
                elif model.status == "active":
                    model.status = "inactive"
        await repo.create("model_audit", "启用模型", user, parent_id=record_id, data={"task": row["parent_id"]})
    return await require_record(record_id, user)


async def detect_photo(photo_id, task, threshold, user):
    path, photo = await photo_file(photo_id, user)
    models = await repo.list("model", user.department_id, parent_id=task, status="active", limit=1)
    active = models[0] if models else None
    if not active:
        raise HTTPException(409, "请先上传、验证并启用对应任务的模型")
    row = await repo.create(
        "detection",
        task,
        user,
        parent_id=photo["album_id"],
        status="running",
        data={
            "photo_id": photo_id,
            "photo_sha256": photo["sha256"],
            "captured_at": photo["captured_at"],
            "model_id": active["id"],
            "model_sha256": active["data"]["sha256"],
            "task": task,
            "threshold": threshold,
        },
    )

    def infer():
        from ultralytics import YOLO

        model_path = work_root() / f"{active['id']}{active['data']['extension']}"
        with model_path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != active["data"]["sha256"]:
                raise ValueError("模型文件校验失败")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != photo["sha256"]:
                raise ValueError("原图校验失败")
        model = YOLO(str(model_path), task="detect")
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            result = model.predict(image, conf=threshold, device="cpu", verbose=False)[0]
        detections = [
            {
                "class_id": int(box.cls.item()),
                "label": str(model.names[int(box.cls.item())]),
                "confidence": float(box.conf.item()),
                "xyxy": box.xyxy[0].tolist(),
            }
            for box in result.boxes
        ]
        counts = {}
        for detection in detections:
            counts[detection["label"]] = counts.get(detection["label"], 0) + 1
        return {"detections": detections, "counts": counts, "image_size": list(result.orig_shape[::-1])}

    try:
        async with model_lock:
            result = await asyncio.to_thread(infer)
        await repo.change(row["id"], user.department_id, status="ready", data={**row["data"], **result})
    except Exception as exc:
        await repo.change(row["id"], user.department_id, status="failed", data={**row["data"], "error": str(exc)[:500]})
        raise HTTPException(422, f"识别失败，记录已保存: {str(exc)[:200]}") from exc
    return await require_record(row["id"], user)
