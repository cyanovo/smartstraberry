"""Field-work API; identity is always supplied by authentication, never request JSON."""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, AwareDatetime

from server.utils.auth_middleware import get_required_user
from yuxi import knowledge_base
from yuxi.repositories.field_work_repository import field_repository as repo
from yuxi.services import field_work_service as work
from yuxi.services.album_service import require_album
from yuxi.services.album_service import photo_file
from yuxi.repositories.album_repository import album_repository
from yuxi.services.control_proposal_service import confirm_control, propose_control, require_thread
from yuxi.services.field_analysis_service import analyze_album
from yuxi.services.field_model_service import activate_model, detect_photo, upload_model

field_work = APIRouter(prefix="/field-work", tags=["field-work"])
Task = Literal["maturity", "disease"]


@field_work.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str, user=Depends(get_required_user)):
    path, photo = await photo_file(photo_id, user)
    work.require_manager(user, photo)
    try:
        await album_repository.delete_photo(photo_id, user.department_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    path.unlink(missing_ok=True)
    path.with_name(f"{photo_id}.thumb.jpg").unlink(missing_ok=True)
    return {"ok": True}


class CaptureInput(BaseModel):
    album_id: str = Field(min_length=1, max_length=32)
    camera_id: int = Field(ge=0, le=32)
    interval_seconds: int = Field(default=60, ge=10, le=86400)


class BackupInput(BaseModel):
    album_id: str
    start: AwareDatetime
    end: AwareDatetime


class DetectionInput(BaseModel):
    photo_id: str
    task: Task = "maturity"
    threshold: float = Field(default=0.5, ge=0.05, le=0.99)


class AnalysisInput(BaseModel):
    album_id: str
    disease_record_ids: list[str] = Field(default_factory=list, max_length=20)
    kb_id: str | None = None
    average_mass_g: float | None = Field(default=None, gt=0, le=500)


class ProposalInput(BaseModel):
    thread_id: str = Field(min_length=1, max_length=128)
    key: Literal["fertigation", "rotation", "irrigation", "ventilation", "light"]
    value: bool
    reason: str = Field(min_length=1, max_length=1000)


class ConfirmationInput(BaseModel):
    thread_id: str
    accept: bool


@field_work.get("/records/{kind}")
async def records(
    kind: Literal["capture", "backup", "shared", "model", "detection", "analysis", "control", "folder"],
    parent_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user=Depends(get_required_user),
):
    if kind == "control":
        if not parent_id:
            raise HTTPException(422, "请指定当前对话")
        await require_thread(parent_id, user)
    rows = await repo.list(kind, user.department_id, parent_id, limit, offset)
    return [r for r in rows if r["status"] != "deleted" and (kind != "control" or r["owner_uid"] == str(user.uid))]


@field_work.post("/captures")
async def create_capture(body: CaptureInput, user=Depends(get_required_user)):
    album = await require_album(body.album_id, user)
    if not album["device_id"]:
        raise HTTPException(422, "请创建绑定设备编号的照片集")
    return await repo.create(
        "capture",
        album["name"],
        user,
        parent_id=body.album_id,
        status="paused",
        data={**body.model_dump(), "restart_policy": "paused"},
    )


@field_work.post("/captures/{record_id}/{action}")
async def capture_action(record_id: str, action: Literal["start", "stop"], user=Depends(get_required_user)):
    return await getattr(work.capture_service, action)(record_id, user)


@field_work.post("/backups")
async def backup(body: BackupInput, user=Depends(get_required_user)):
    if body.start > body.end:
        raise HTTPException(422, "开始时间不能晚于结束时间")
    return await work.create_backup(body.album_id, body.start, body.end, user)


@field_work.post("/shared")
async def shared(
    file: UploadFile = File(...),
    folder: str = Form(""),
    version_note: str = Form("", max_length=500),
    user=Depends(get_required_user),
):
    return await work.shared_upload(file, folder, user, version_note)


@field_work.post("/folders")
async def folder(name: str = Form(...), user=Depends(get_required_user)):
    name = work.folder_name(name)
    if not name:
        raise HTTPException(422, "目录不能为空")
    return await repo.create("folder", name, user, parent_id=name)


@field_work.delete("/shared/{record_id}")
async def remove_shared(record_id: str, user=Depends(get_required_user)):
    await work.delete_shared(record_id, user)
    return {"ok": True}


@field_work.get("/files/{record_id}")
async def download(record_id: str, user=Depends(get_required_user)):
    path, row = await work.download_record(record_id, user)
    return FileResponse(
        path,
        filename=row["name"],
        media_type="application/octet-stream",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@field_work.post("/models")
async def model(
    file: UploadFile = File(...), task: Task = Form(...), trusted: bool = Form(False), user=Depends(get_required_user)
):
    return await upload_model(file, task, trusted, user)


@field_work.post("/models/{record_id}/activate")
async def activate(record_id: str, user=Depends(get_required_user)):
    return await activate_model(record_id, user)


@field_work.post("/detections")
async def detection(body: DetectionInput, user=Depends(get_required_user)):
    return await detect_photo(body.photo_id, body.task, body.threshold, user)


@field_work.get("/knowledge")
async def knowledge(user=Depends(get_required_user)):
    return (await knowledge_base.get_databases_by_user(user)).get("databases", [])


@field_work.post("/analyses")
async def analysis(body: AnalysisInput, user=Depends(get_required_user)):
    return await analyze_album(body.album_id, body.kb_id, body.average_mass_g, user, body.disease_record_ids)


@field_work.post("/control/propose")
async def propose(body: ProposalInput, user=Depends(get_required_user)):
    return await propose_control(body.thread_id, body.key, body.value, body.reason, user)


@field_work.post("/control/{record_id}/confirm")
async def confirm(record_id: str, body: ConfirmationInput, user=Depends(get_required_user)):
    return await confirm_control(record_id, body.thread_id, body.accept, user)
