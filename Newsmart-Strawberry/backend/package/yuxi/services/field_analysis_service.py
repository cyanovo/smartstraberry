"""Evidence-based visible-fruit estimates, never cumulative counts across photos."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from yuxi import knowledge_base
from yuxi.repositories.field_work_repository import field_repository as repo
from yuxi.repositories.sensor_history_repository import sensor_history_repository
from yuxi.services.album_service import require_album


def estimate_visible(records, average_mass_g=None):
    successful = [r for r in records if r["status"] == "ready" and r["data"]["task"] == "maturity"]
    successful.sort(
        key=lambda r: (datetime.fromisoformat(r["data"]["captured_at"]), datetime.fromisoformat(r["created_at"])),
        reverse=True,
    )
    if not successful:
        return {"status": "insufficient_data", "reason": "没有成功的成熟度识别记录"}
    latest = successful[0]
    counts = latest["data"]["counts"]
    ripe = sum(n for label, n in counts.items() if label.lower() == "ripe")
    return {
        "status": "visible_snapshot_only",
        "detection_id": latest["id"],
        "photo_id": latest["data"]["photo_id"],
        "captured_at": latest["data"]["captured_at"],
        "visible_fruits": sum(counts.values()),
        "visible_ripe": ripe,
        "average_mass_g": average_mass_g,
        "visible_ripe_mass_g": round(ripe * average_mass_g, 2) if average_mass_g is not None else None,
        "limitations": ["仅最新拍摄视野，不累加重复照片", "未校正遮挡、漏检、病害损失和后续成熟率", "不是整棚产量预测"],
    }


async def retrieve_knowledge(kb_id, user):
    """Isolate external retrieval failures without disguising permission failures."""
    knowledge = {"status": "not_selected", "kb_id": kb_id, "evidence": None}
    if kb_id:
        identity = {"uid": user.uid, "role": user.role, "department_id": user.department_id}
        if not await knowledge_base.check_accessible(identity, kb_id):
            raise HTTPException(403, "无权访问所选知识库")
        try:
            evidence = await knowledge_base.aquery("草莓成熟采收、病虫害与产量评估注意事项", kb_id)
            if hasattr(evidence, "model_dump"):
                evidence = evidence.model_dump(mode="json")
            knowledge.update(status="ready", evidence=evidence)
        except Exception as exc:
            knowledge.update(status="unavailable", error=str(exc)[:300])
    return knowledge


async def analyze_album(album_id, kb_id, average_mass_g, user, disease_record_ids=None):
    """Skill demonstration orchestration: fetch, correlate, estimate, persist."""
    album = await require_album(album_id, user)
    selected_disease = []
    if len(disease_record_ids or []) > 20:
        raise HTTPException(422, "最多选择 20 条病虫害识别记录")
    for record_id in dict.fromkeys(disease_record_ids or []):
        row = await repo.get(record_id, user.department_id, "detection")
        if not row:
            raise HTTPException(404, "所选病虫害识别记录不存在或无权访问")
        if row["status"] != "ready" or row["data"].get("task") != "disease":
            raise HTTPException(422, "只能选择成功的病虫害识别记录")
        selected_disease.append(row)
    records = await repo.list("detection", user.department_id, parent_id=album_id, limit=1000)
    estimate = estimate_visible(records, average_mass_g)
    disease = [r for r in records if r["status"] == "ready" and r["data"]["task"] == "disease"]
    disease.sort(
        key=lambda r: (datetime.fromisoformat(r["data"]["captured_at"]), datetime.fromisoformat(r["created_at"])),
        reverse=True,
    )
    sensors = {"total": 0, "items": []}
    anchor = datetime.fromisoformat(estimate["captured_at"]) if estimate.get("captured_at") else datetime.now(UTC)
    if album["device_id"]:
        sensors = await sensor_history_repository.query(
            device_id=album["device_id"], start=anchor - timedelta(hours=24), end=anchor, limit=24
        )
    knowledge = await retrieve_knowledge(kb_id, user)
    result = {
        "album": album,
        "estimate": estimate,
        "latest_disease": disease[0] if disease else None,
        "selected_disease_records": selected_disease,
        "disease_evidence_source": "user_selected" if selected_disease else "album_latest",
        "disease_scope_note": "手动记录保留原照片集来源，跨照片集结果不能视为当前草莓簇患病或直接扣减产量",
        "sensor_history": sensors,
        "sensor_window": {"start": (anchor - timedelta(hours=24)).isoformat(), "end": anchor.isoformat()},
        "image_age_hours": round((datetime.now(UTC) - anchor).total_seconds() / 3600, 2),
        "knowledge": knowledge,
        "analyzed_at": datetime.now(UTC).isoformat(),
        "detection_ids": [r["id"] for r in records[:100]],
        "failed_detections": sum(r["status"] in ("failed", "interrupted") for r in records),
        "mass_basis": "用户提供的实测平均单果质量" if average_mass_g is not None else "未提供称重，不输出重量",
    }
    return await repo.create("analysis", album["name"], user, parent_id=album_id, data=result)
