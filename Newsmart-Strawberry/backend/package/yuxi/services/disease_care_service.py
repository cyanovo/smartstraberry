"""Record-backed powdery mildew guidance with explicitly confirmed device requests."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from yuxi import knowledge_base
from yuxi.repositories.field_work_repository import field_repository as repo
from yuxi.services.control_proposal_service import require_thread
from yuxi.services.field_work_service import require_record
from yuxi.services.iot_service import iot_service

ACTIONS = [
    {"key": "irrigation", "value": False, "label": "停止滴灌"},
    {"key": "ventilation", "value": True, "label": "打开通风"},
    {"key": "rotation", "value": True, "label": "打开旋转"},
    {"key": "light", "value": True, "label": "打开光照"},
]

ANSWER = """草莓白粉病防治建议

发病原因
白粉病由真菌侵染引起，可随带病种苗及病残体传播。温湿度适宜、棚内通风不足、植株过密、嫩叶生长旺盛和氮肥偏多时，病害容易扩展。常见表现为叶片背面或果面出现白色粉状霉层、叶缘上卷；仍需结合原图和现场症状复核，环境读数不能单独确诊。

解决方案
及时隔离和清除明显病叶、病果，装袋带离种植区并清洁工具；适度疏叶，改善冠层通风，避免过量施氮。持续观察新叶、花和果实，记录病斑变化。需要用药时，选择当地登记用于草莓白粉病的药剂，严格按标签使用并轮换作用机制，遵守安全间隔期及授粉昆虫保护要求，不自行加大浓度。

注意事项
白粉病管理不能只靠设备开关。暂停滴灌仅作为短时调整，须核对基质含水量，避免植株缺水；通风同时关注外界温度与湿度。补光应结合光周期及温度，不能代替杀菌处理；旋转前确认机构周边无人、无阻挡。调整后继续观察传感器与植株状态，及时恢复适宜灌溉。

设备调整
停止滴灌、打开通风、打开旋转、打开光照。是否确认发送以上四项控制指令？"""


async def analyze_disease(thread_id, record_ids, kb_id, user, progress=None, *, question="分析所选病虫害记录"):
    await require_thread(thread_id, user)
    if progress:
        await progress({"type": "stage", "text": "正在读取病虫害识别记录"})
    records = []
    for record_id in dict.fromkeys(record_ids):
        row = await require_record(record_id, user, "detection")
        if row["status"] != "ready" or row["data"].get("task") != "disease":
            raise HTTPException(422, "请选择已完成的病虫害识别记录")
        records.append(row)
    if not records:
        raise HTTPException(422, "请先选择病虫害识别记录")
    tools = [{"name": "读取病虫害识别记录", "status": "ready", "result": records}]
    if progress:
        await progress({"type": "tools", "tools": list(tools)})
        await progress({"type": "stage", "text": "正在读取实时传感器与设备状态"})
    try:
        dashboard = (await iot_service.get_dashboard()).model_dump(mode="json")
        tools.append({"name": "读取实时传感器与设备状态", "status": "ready", "result": dashboard})
    except Exception:
        dashboard = None
        tools.append({"name": "读取实时传感器与设备状态", "status": "unavailable", "result": "读取失败，控制不可用"})
    if progress:
        await progress({"type": "tools", "tools": list(tools)})
    if kb_id:
        identity = {"uid": user.uid, "role": user.role, "department_id": user.department_id}
        if not await knowledge_base.check_accessible(identity, kb_id):
            raise HTTPException(403, "无权访问所选知识库")
        if progress:
            await progress({"type": "stage", "text": "正在检索草莓白粉病知识资料"})
        try:
            evidence = await knowledge_base.aquery("草莓白粉病的发病原因、防治措施与用药注意事项", kb_id)
            if hasattr(evidence, "model_dump"):
                evidence = evidence.model_dump(mode="json")
            tools.append({"name": "检索草莓白粉病知识", "status": "ready", "result": evidence})
        except Exception:
            tools.append({
                "name": "检索草莓白粉病知识", "status": "unavailable",
                "result": "暂未获取知识库资料，以下为通用防治建议",
            })
    if progress:
        await progress({"type": "tools", "tools": list(tools)})
        await progress({"type": "stage", "text": "正在整理防治方案与设备建议"})
    control = (dashboard or {}).get("device_control") or {}
    available = control.get("online") and control.get("broker_connected") and control.get("protocol") == "strawberry"
    return await repo.create(
        "disease_care",
        "草莓白粉病防治建议",
        user,
        parent_id=thread_id,
        status="pending" if available else "unavailable",
        data={
            "question": question,
            "record_ids": [r["id"] for r in records],
            "tools": tools,
            "answer": ANSWER,
            "actions": ACTIONS,
            "kb_id": kb_id,
            "snapshot": dashboard,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=3)).isoformat(),
            "message": "等待确认，尚未发送指令" if available else "设备离线或协议不支持，请恢复连接后重新分析",
        },
    )


async def confirm_disease(record_id, thread_id, accept, user):
    await require_thread(thread_id, user)
    row = await require_record(record_id, user, "disease_care")
    if row["owner_uid"] != str(user.uid) or row["parent_id"] != thread_id:
        raise HTTPException(403, "确认人与对话不匹配")
    if row["status"] != "pending":
        return row
    if not accept:
        await repo.change(
            record_id,
            user.department_id,
            status="rejected",
            expected="pending",
            data={**row["data"], "message": "已取消，未发送指令"},
        )
        return await require_record(record_id, user, "disease_care")
    if datetime.fromisoformat(row["data"]["expires_at"]) < datetime.now(UTC):
        await repo.change(
            record_id,
            user.department_id,
            status="expired",
            expected="pending",
            data={**row["data"], "message": "已过期，未发送指令"},
        )
        raise HTTPException(409, "建议已过期，请重新分析")
    dashboard = (await iot_service.get_dashboard()).model_dump(mode="json")
    control = dashboard["device_control"]
    if not control.get("online") or not control.get("broker_connected") or control.get("protocol") != "strawberry":
        raise HTTPException(409, "设备离线或协议不支持，未发送指令")
    if not await repo.change(record_id, user.department_id, status="sending", expected="pending"):
        return await require_record(record_id, user, "disease_care")
    results = []
    # Persist each outcome; a restart must never automatically resend physical commands.
    for action in ACTIONS:
        try:
            sent = await iot_service.control_actuator(action["key"], action["value"])
            status = "sent_unconfirmed" if sent else "failed"
        except Exception:
            status = "unknown"
        results.append({**action, "status": status})
        await repo.change(
            record_id,
            user.department_id,
            status="sending",
            data={
                **row["data"],
                "results": results,
                "confirmed_by": str(user.uid),
                "confirmed_at": datetime.now(UTC).isoformat(),
            },
        )
    status = "sent_unconfirmed" if all(r["status"] == "sent_unconfirmed" for r in results) else "partial_failure"
    await repo.change(
        record_id,
        user.department_id,
        status=status,
        data={
            **row["data"],
            "results": results,
            "confirmed_by": str(user.uid),
            "confirmed_at": datetime.now(UTC).isoformat(),
            "message": "控制请求已发送，实际动作请核验设备"
            if status == "sent_unconfirmed"
            else "存在失败或未知指令，请逐项检查，勿重复发送",
        },
    )
    return await require_record(record_id, user, "disease_care")
