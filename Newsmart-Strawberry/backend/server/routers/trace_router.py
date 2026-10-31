"""
番茄溯源系统 — API 路由

完整溯源链路：
种子来源 → 地块规划 → 播种 → 田间管理 → 生长监测 → 采摘 → 质检 → 包装 → 销售 → 消费者扫码查询
"""

import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from server.utils.auth_middleware import get_required_user
from yuxi.storage.minio import get_minio_client
from yuxi.traceability import db, blockchain

trace = APIRouter(prefix="/trace", tags=["番茄溯源"])

# 上传目录 — 使用 Docker 卷路径
_SAVES_DIR = (
    Path("/app/saves")
    if Path("/app/saves").exists()
    else Path(__file__).resolve().parent.parent.parent.parent / "docker" / "volumes" / "greenhouse"
)
UPLOADS_DIR = _SAVES_DIR / "trace_uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# 初始化数据库
db.init_db()


# ══════════════════════════════════════════════════════════════════════
#  地块 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/plot/create")
async def create_plot(data: db.PlotCreate, _=Depends(get_required_user)):
    return {"ok": True, "plot": db.create_plot(data).model_dump()}


@trace.get("/plot/list")
async def list_plots(_=Depends(get_required_user)):
    plots = db.list_plots()
    return {"ok": True, "count": len(plots), "plots": [p.model_dump() for p in plots]}


@trace.get("/plot/{plot_id}")
async def get_plot(plot_id: str, _=Depends(get_required_user)):
    plot = db.get_plot(plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    return {"ok": True, "plot": plot.model_dump()}


@trace.put("/plot/{plot_id}")
async def update_plot(plot_id: str, patch: db.PlotUpdate, _=Depends(get_required_user)):
    plot = db.update_plot(plot_id, patch)
    if not plot:
        raise HTTPException(status_code=404, detail="地块不存在")
    return {"ok": True, "plot": plot.model_dump()}


@trace.delete("/plot/{plot_id}")
async def delete_plot(plot_id: str, _=Depends(get_required_user)):
    db.delete_plot(plot_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
#  种子 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/seed/create")
async def create_seed(data: db.SeedCreate, _=Depends(get_required_user)):
    return {"ok": True, "seed": db.create_seed(data).model_dump()}


@trace.get("/seed/list")
async def list_seeds(_=Depends(get_required_user)):
    seeds = db.list_seeds()
    return {"ok": True, "count": len(seeds), "seeds": [s.model_dump() for s in seeds]}


@trace.get("/seed/{seed_id}")
async def get_seed(seed_id: str, _=Depends(get_required_user)):
    seed = db.get_seed(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="种子不存在")
    return {"ok": True, "seed": seed.model_dump()}


@trace.put("/seed/{seed_id}")
async def update_seed(seed_id: str, patch: db.SeedUpdate, _=Depends(get_required_user)):
    seed = db.update_seed(seed_id, patch)
    if not seed:
        raise HTTPException(status_code=404, detail="种子不存在")
    return {"ok": True, "seed": seed.model_dump()}


@trace.delete("/seed/{seed_id}")
async def delete_seed(seed_id: str, _=Depends(get_required_user)):
    db.delete_seed(seed_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
#  种植批次 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/batch/create")
async def create_batch(data: db.BatchCreate, _=Depends(get_required_user)):
    try:
        batch = db.create_batch(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    blockchain.add_block(
        {
            "event": "创建种植批次",
            "batch_id": batch.id,
            "batch_code": batch.batch_code,
        }
    )
    return {"ok": True, "batch": batch.model_dump()}


@trace.get("/batch/list")
async def list_batches(limit: int = 50, _=Depends(get_required_user)):
    batches = db.list_batches(limit)
    return {"ok": True, "count": len(batches), "batches": [b.model_dump() for b in batches]}


@trace.get("/batch/{batch_id}")
async def get_batch(batch_id: str, _=Depends(get_required_user)):
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return {"ok": True, "batch": batch.model_dump()}


@trace.put("/batch/{batch_id}")
async def update_batch(batch_id: str, patch: db.BatchUpdate, _=Depends(get_required_user)):
    batch = db.update_batch(batch_id, patch)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return {"ok": True, "batch": batch.model_dump()}


@trace.delete("/batch/{batch_id}")
async def delete_batch(batch_id: str, _=Depends(get_required_user)):
    db.delete_batch(batch_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
#  农事操作 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/activity/add")
async def add_activity(data: db.ActivityCreate, _=Depends(get_required_user)):
    activity = db.add_activity(data)
    return {"ok": True, "activity": activity.model_dump()}


@trace.get("/activity/list/{batch_id}")
async def list_activities(batch_id: str, _=Depends(get_required_user)):
    activities = db.list_activities(batch_id)
    return {"ok": True, "count": len(activities), "activities": [a.model_dump() for a in activities]}


@trace.delete("/activity/{activity_id}")
async def delete_activity(activity_id: str, _=Depends(get_required_user)):
    db.delete_activity(activity_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
#  环境数据 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/environment/add")
async def add_environment(data: db.EnvironmentCreate, _=Depends(get_required_user)):
    env = db.add_environment(data)
    return {"ok": True, "environment": env.model_dump()}


@trace.get("/environment/list/{batch_id}")
async def list_environments(batch_id: str, _=Depends(get_required_user)):
    envs = db.list_environments(batch_id)
    return {"ok": True, "count": len(envs), "environments": [e.model_dump() for e in envs]}


@trace.delete("/environment/{env_id}")
async def delete_environment(env_id: str, _=Depends(get_required_user)):
    db.delete_environment(env_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
#  采摘记录 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/harvest/add")
async def add_harvest(data: db.HarvestCreate, _=Depends(get_required_user)):
    harvest = db.add_harvest(data)
    blockchain.add_block(
        {
            "event": "记录采摘",
            "batch_id": data.batch_id,
            "harvest_date": data.harvest_date,
            "yield_kg": data.yield_kg,
            "grade": data.grade,
        }
    )
    return {"ok": True, "harvest": harvest.model_dump()}


@trace.get("/harvest/list/{batch_id}")
async def list_harvests(batch_id: str, _=Depends(get_required_user)):
    harvests = db.list_harvests(batch_id)
    return {"ok": True, "count": len(harvests), "harvests": [h.model_dump() for h in harvests]}


# ══════════════════════════════════════════════════════════════════════
#  质检记录 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/inspection/add")
async def add_inspection(data: db.InspectionCreate, _=Depends(get_required_user)):
    inspection = db.add_inspection(data)
    blockchain.add_block(
        {
            "event": "质检记录",
            "batch_id": data.batch_id,
            "inspection_type": data.inspection_type,
            "result": data.result,
        }
    )
    return {"ok": True, "inspection": inspection.model_dump()}


@trace.get("/inspection/list/{batch_id}")
async def list_inspections(batch_id: str, _=Depends(get_required_user)):
    inspections = db.list_inspections(batch_id)
    return {"ok": True, "count": len(inspections), "inspections": [i.model_dump() for i in inspections]}


# ══════════════════════════════════════════════════════════════════════
#  包装记录 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/package/add")
async def add_package(data: db.PackageCreate, _=Depends(get_required_user)):
    package = db.add_package(data)
    blockchain.add_block(
        {
            "event": "记录包装",
            "batch_id": data.batch_id,
            "weight_kg": data.weight_kg,
            "lot_number": data.lot_number,
        }
    )
    return {"ok": True, "package": package.model_dump()}


@trace.get("/package/list/{batch_id}")
async def list_packages(batch_id: str, _=Depends(get_required_user)):
    packages = db.list_packages(batch_id)
    return {"ok": True, "count": len(packages), "packages": [p.model_dump() for p in packages]}


# ══════════════════════════════════════════════════════════════════════
#  溯源查询 API（消费者端）
# ══════════════════════════════════════════════════════════════════════


@trace.get("/query/{code}")
async def trace_query(code: str):
    """消费者扫码查询 — 根据溯源码返回完整溯源报告（无需认证）"""
    report = db.get_trace_report(code)
    if not report:
        raise HTTPException(status_code=404, detail="溯源码无效或已失效")

    bc = blockchain.verify_chain()
    report.blockchain_verified = bc.get("valid", False)

    return {"ok": True, "report": report.model_dump()}


@trace.get("/query/batch/{batch_code}")
async def trace_by_batch_code(batch_code: str):
    """通过批次编号查询溯源信息（无需认证）"""
    batch = db.get_batch_by_code(batch_code)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    activities_summary = {}
    for a in batch.activities:
        t = a.get("type", "其他")
        activities_summary[t] = activities_summary.get(t, 0) + 1

    env_data = batch.environments
    env_summary = {}
    if env_data:
        temps = [e["temperature"] for e in env_data if e.get("temperature") is not None]
        humids = [e["humidity"] for e in env_data if e.get("humidity") is not None]
        if temps:
            env_summary["avg_temp"] = round(sum(temps) / len(temps), 1)
        if humids:
            env_summary["avg_humidity"] = round(sum(humids) / len(humids), 1)

    growth_photos = db.list_batch_photos(batch.id, "growth")
    harvest_photos = db.list_batch_photos(batch.id, "harvest")

    report = {
        "batch_code": batch.batch_code,
        "plot_name": batch.plot.name if batch.plot else "",
        "plot_location": batch.plot.location if batch.plot else "",
        "seed_variety": batch.seed.variety if batch.seed else "",
        "seed_supplier": batch.seed.supplier if batch.seed else "",
        "plant_date": batch.plant_date or "",
        "harvest_date": batch.harvests[-1].get("harvest_date") if batch.harvests else None,
        "harvest_grade": batch.harvests[-1].get("grade") if batch.harvests else None,
        "harvest_yield_kg": batch.harvests[-1].get("yield_kg") if batch.harvests else None,
        "activities_summary": activities_summary,
        "activities_detail": [
            {
                "type": a.get("type"),
                "datetime": a.get("datetime"),
                "detail": a.get("detail"),
                "materials": a.get("materials"),
            }
            for a in batch.activities
        ],
        "environment_summary": env_summary,
        "inspections": [
            {"type": i.get("inspection_type"), "result": i.get("result"), "lab": i.get("lab_name")}
            for i in batch.inspections
        ],
        "package_info": {
            "package_date": batch.packages[-1].get("package_date"),
            "weight_kg": batch.packages[-1].get("weight_kg"),
            "lot_number": batch.packages[-1].get("lot_number"),
        }
        if batch.packages
        else None,
        "growth_photos": [p.model_dump() for p in growth_photos],
        "harvest_photos": [p.model_dump() for p in harvest_photos],
    }

    return {"ok": True, "report": report}


# ══════════════════════════════════════════════════════════════════════
#  图片上传 API
# ══════════════════════════════════════════════════════════════════════


@trace.post("/upload/{batch_id}")
async def upload_photo(
    batch_id: str,
    file: UploadFile = File(...),
    photo_type: str = Form("growth"),
    photo_date: str = Form(""),
    note: str = Form(""),
    _=Depends(get_required_user),
):
    """上传批次相关照片（生长日常/采摘时）"""
    batch = db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    if photo_type not in ("growth", "harvest"):
        raise HTTPException(status_code=400, detail="照片类型必须是 growth 或 harvest")

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {ext}")

    filename = f"{photo_type}_{uuid.uuid4().hex[:8]}{ext}"
    content = await file.read()
    object_name = f"traceability/{batch_id}/{filename}"
    minio_client = get_minio_client()
    upload_result = await minio_client.aupload_file(
        "public",
        object_name,
        content,
        content_type=file.content_type,
    )

    if not photo_date:
        photo_date = datetime.now().strftime("%Y-%m-%d")
    data = db.BatchPhotoCreate(
        batch_id=batch_id, photo_type=photo_type, photo_date=photo_date, file_name=file.filename or filename, note=note
    )
    photo = db.add_batch_photo(data, upload_result.url)

    return {"ok": True, "photo": photo.model_dump(), "url": upload_result.url}


@trace.get("/photos/{batch_id}")
async def list_photos(batch_id: str, photo_type: Optional[str] = None, _=Depends(get_required_user)):
    """获取批次的照片列表"""
    photos = db.list_batch_photos(batch_id, photo_type)
    return {"ok": True, "count": len(photos), "photos": [p.model_dump() for p in photos]}


@trace.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str, _=Depends(get_required_user)):
    """删除照片"""
    photo = db.get_batch_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    if photo.file_path.startswith(("http://", "https://")):
        from urllib.parse import urlparse

        parts = urlparse(photo.file_path).path.lstrip("/").split("/", 1)
        if len(parts) == 2:
            await get_minio_client().adelete_file(parts[0], parts[1])
    elif Path(photo.file_path).exists():
        Path(photo.file_path).unlink()
    db.delete_batch_photo(photo_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
#  溯源事件 API
# ══════════════════════════════════════════════════════════════════════


@trace.get("/events/{batch_id}")
async def list_events(batch_id: str, _=Depends(get_required_user)):
    events = db.list_events(batch_id)
    return {"ok": True, "count": len(events), "events": [e.model_dump() for e in events]}


# ══════════════════════════════════════════════════════════════════════
#  区块链 API
# ══════════════════════════════════════════════════════════════════════


@trace.get("/blockchain/status")
async def blockchain_status(_=Depends(get_required_user)):
    chain = blockchain.get_chain()
    verification = blockchain.verify_chain()
    return {
        "ok": True,
        "block_count": len(chain),
        "is_valid": verification["valid"],
        "message": verification["message"],
        "chain": chain[-10:],
    }


@trace.get("/blockchain/verify")
async def blockchain_verify(_=Depends(get_required_user)):
    return {"ok": True, **blockchain.verify_chain()}


# ══════════════════════════════════════════════════════════════════════
#  统计 API
# ══════════════════════════════════════════════════════════════════════


@trace.get("/stats")
async def get_stats(_=Depends(get_required_user)):
    stats = db.get_stats()
    chain = blockchain.get_chain()
    verification = blockchain.verify_chain()
    return {
        "ok": True,
        **stats,
        "blockchain_blocks": len(chain),
        "blockchain_valid": verification["valid"],
    }


# ══════════════════════════════════════════════════════════════════════
#  二维码 API
# ══════════════════════════════════════════════════════════════════════


@trace.get("/qr/generate/{trace_code}")
async def generate_qr(trace_code: str, _=Depends(get_required_user)):
    """生成溯源码的二维码图片（返回 base64）"""
    import base64

    try:
        import qrcode
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 qrcode: pip install qrcode[pil]")

    tc = db.get_trace_code(trace_code)
    if not tc:
        raise HTTPException(status_code=404, detail="溯源码不存在")

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(trace_code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#e74c3c", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "ok": True,
        "trace_code": trace_code,
        "image_base64": f"data:image/png;base64,{img_base64}",
    }


@trace.get("/qr/image/{trace_code}")
async def get_qr_image(trace_code: str):
    """直接返回二维码图片（PNG 格式，无需认证）"""
    try:
        import qrcode
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 qrcode: pip install qrcode[pil]")

    tc = db.get_trace_code(trace_code)
    if not tc:
        raise HTTPException(status_code=404, detail="溯源码不存在")

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(trace_code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#e74c3c", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer, media_type="image/png", headers={"Content-Disposition": f'attachment; filename="qr_{trace_code}.png"'}
    )


@trace.post("/qr/decode")
async def decode_qr(file: UploadFile = File(...), _=Depends(get_required_user)):
    """识别上传图片中的二维码"""
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        from PIL import Image
    except ImportError:
        raise HTTPException(status_code=500, detail="请安装 pyzbar 和 Pillow: pip install pyzbar Pillow")

    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        img = Image.open(io.BytesIO(content))
        decoded = pyzbar_decode(img)

        if not decoded:
            return {"ok": False, "detail": "未识别到二维码"}

        qr_data = decoded[0].data.decode("utf-8")

        return {
            "ok": True,
            "decoded_data": qr_data,
            "count": len(decoded),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"识别失败: {str(e)}")
