"""Only authenticated human confirmation may turn a proposal into an MQTT request."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from yuxi.iot.mqtt_client import STRAWBERRY_TOPICS
from yuxi.repositories.conversation_repository import ConversationRepository
from yuxi.repositories.field_work_repository import field_repository as repo
from yuxi.services.field_work_service import require_record
from yuxi.services.iot_service import iot_service
from yuxi.storage.postgres.manager import pg_manager


async def require_thread(thread_id, user):
    async with pg_manager.get_async_session_context() as session:
        conversation = await ConversationRepository(session).get_conversation_by_thread_id(thread_id)
        if not conversation or str(conversation.uid) != str(user.uid):
            raise HTTPException(404, "对话不存在或无权访问")


async def propose_control(thread_id, key, value, reason, user):
    await require_thread(thread_id, user)
    key = "irrigation" if key == "pump" else key
    if key not in STRAWBERRY_TOPICS:
        raise HTTPException(422, "不支持的执行器")
    dashboard = (await iot_service.get_dashboard()).model_dump(mode="json")
    control = dashboard["device_control"]
    if not control.get("online") or not control.get("broker_connected"):
        raise HTTPException(409, "设备离线，不生成可执行建议")
    return await repo.create(
        "control",
        reason[:255],
        user,
        parent_id=thread_id,
        status="pending",
        data={
            "key": key,
            "value": value,
            "reason": reason,
            "snapshot": dashboard,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=3)).isoformat(),
            "message": "请在当前对话的设备建议面板明确接受；未确认前不发送指令",
        },
    )


async def confirm_control(record_id, thread_id, accept, user):
    await require_thread(thread_id, user)
    row = await require_record(record_id, user, "control")
    if row["owner_uid"] != str(user.uid) or row["parent_id"] != thread_id:
        raise HTTPException(403, "确认人与对话不匹配")
    if row["status"] != "pending":
        return row
    if not accept:
        await repo.change(record_id, user.department_id, status="rejected", expected="pending")
        return await require_record(record_id, user)
    if datetime.fromisoformat(row["data"]["expires_at"]) < datetime.now(UTC):
        await repo.change(record_id, user.department_id, status="expired", expected="pending")
        raise HTTPException(409, "建议已过期，请重新读取传感器并生成建议")
    current = (await iot_service.get_dashboard()).model_dump(mode="json")
    previous = row["data"]["snapshot"]
    if not current["device_control"].get("online") or not current["device_control"].get("broker_connected"):
        raise HTTPException(409, "设备已离线，未发送指令")
    for section in ("air", "soil"):
        before = previous.get(section) or {}
        after = current.get(section) or {}
        if set(before) != set(after):
            raise HTTPException(409, "传感器状态变化，请重新生成建议")
        for key in before:
            if key == "timestamp":
                continue
            if before[key] != after[key]:
                raise HTTPException(409, "传感器读数已变化，请重新生成建议")
    if previous["device_control"].get("states") != current["device_control"].get("states"):
        raise HTTPException(409, "设备状态已变化，请重新生成建议")
    claimed = await repo.change(record_id, user.department_id, status="sending", expected="pending")
    if not claimed:
        return await require_record(record_id, user)
    try:
        sent = await iot_service.control_actuator(row["data"]["key"], row["data"]["value"])
        status = "sent_unconfirmed" if sent else "failed"
        data = {
            **row["data"],
            "confirmed_by": str(user.uid),
            "confirmed_at": datetime.now(UTC).isoformat(),
            "message": "已发送，实际执行未确认" if sent else "发送失败",
        }
    except Exception as exc:
        status, data = "unknown", {**row["data"], "error": str(exc)[:300]}
    await repo.change(record_id, user.department_id, status=status, data=data)
    return await require_record(record_id, user)
