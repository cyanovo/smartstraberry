import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest
from fastapi import HTTPException

from yuxi.services import disease_care_service as care


@pytest.fixture
def setup(monkeypatch):
    user = SimpleNamespace(uid="owner", department_id=1, role="user")
    dashboard = {
        "air": {"temp": 23, "humidity": 70},
        "soil": None,
        "device_control": {"online": True, "broker_connected": True, "protocol": "strawberry"},
    }
    row = {
        "id": "record",
        "owner_uid": "owner",
        "parent_id": "thread",
        "status": "pending",
        "data": {"expires_at": (datetime.now(UTC) + timedelta(minutes=3)).isoformat()},
    }
    monkeypatch.setattr(care, "require_thread", AsyncMock())
    monkeypatch.setattr(care, "require_record", AsyncMock(side_effect=lambda *a: deepcopy(row)))
    monkeypatch.setattr(
        care.iot_service,
        "get_dashboard",
        AsyncMock(return_value=SimpleNamespace(model_dump=lambda **kw: deepcopy(dashboard))),
    )
    publish = AsyncMock(return_value=True)
    monkeypatch.setattr(care.iot_service, "control_actuator", publish)

    async def change(_id, _dept, *, status, data=None, expected=None):
        if expected and row["status"] != expected:
            return False
        row["status"] = status
        if data is not None:
            row["data"] = deepcopy(data)
        return True

    async def create(kind, name, owner, **kwargs):
        return {"id": "new", "kind": kind, "name": name, **kwargs}

    monkeypatch.setattr(care.repo, "change", change)
    monkeypatch.setattr(care.repo, "create", AsyncMock(side_effect=create))
    return user, dashboard, row, publish


def test_analysis_preserves_detection_and_never_sends(setup, monkeypatch):
    user, dashboard, _, publish = setup
    detection = {"id": "d1", "status": "ready", "data": {"task": "disease", "counts": {"leaf_spot": 1}}}
    monkeypatch.setattr(care, "require_record", AsyncMock(return_value=detection))
    result = asyncio.run(care.analyze_disease("thread", ["d1", "d1"], None, user, question="看看这片叶子怎么处理？"))
    assert result["data"]["question"] == "看看这片叶子怎么处理？"
    assert result["status"] == "pending"
    assert result["data"]["record_ids"] == ["d1"]
    assert result["data"]["tools"][0]["result"] == [detection]
    assert result["data"]["tools"][1]["result"] == dashboard
    assert "白粉病" in result["data"]["answer"]
    assert len(result["data"]["actions"]) == 4
    publish.assert_not_awaited()


def test_confirmation_sends_exactly_four_once(setup):
    user, _, row, publish = setup

    async def run():
        await asyncio.gather(
            care.confirm_disease("record", "thread", True, user), care.confirm_disease("record", "thread", True, user)
        )
        await care.confirm_disease("record", "thread", True, user)

    asyncio.run(run())
    assert publish.await_args_list == [
        call("irrigation", False),
        call("ventilation", True),
        call("rotation", True),
        call("light", True),
    ]
    assert row["status"] == "sent_unconfirmed"
    assert len(row["data"]["results"]) == 4


def test_analysis_reports_real_knowledge_progress(setup, monkeypatch):
    user, _, _, publish = setup
    detection = {"id": "d1", "status": "ready", "data": {"task": "disease"}}
    monkeypatch.setattr(care, "require_record", AsyncMock(return_value=detection))
    monkeypatch.setattr(care.knowledge_base, "check_accessible", AsyncMock(return_value=True))
    query = AsyncMock(return_value={"content": "草莓白粉病知识证据"})
    monkeypatch.setattr(care.knowledge_base, "aquery", query)
    progress = AsyncMock()
    result = asyncio.run(care.analyze_disease("thread", ["d1"], "kb1", user, progress))
    query.assert_awaited_once()
    events = [item.args[0] for item in progress.await_args_list]
    assert [event["type"] for event in events] == ["stage", "tools", "stage", "tools", "stage", "tools", "stage"]
    assert events[-2]["tools"][-1]["result"] == {"content": "草莓白粉病知识证据"}
    assert result["data"]["kb_id"] == "kb1"
    publish.assert_not_awaited()


@pytest.mark.parametrize("case", ["owner", "thread", "expired", "offline", "protocol", "rejected"])
def test_confirmation_guards_never_send(setup, case):
    user, dashboard, row, publish = setup
    if case == "owner":
        row["owner_uid"] = "another-user"
    elif case == "thread":
        row["parent_id"] = "another-thread"
    elif case == "expired":
        row["data"]["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    elif case == "offline":
        dashboard["device_control"]["online"] = False
    elif case == "protocol":
        dashboard["device_control"]["protocol"] = "tomato"
    if case == "rejected":
        asyncio.run(care.confirm_disease("record", "thread", False, user))
        assert row["status"] == "rejected"
    else:
        with pytest.raises(HTTPException):
            asyncio.run(care.confirm_disease("record", "thread", True, user))
    publish.assert_not_awaited()


def test_partial_failure_keeps_each_outcome_and_does_not_retry(setup):
    user, _, row, publish = setup
    publish.side_effect = [True, False, RuntimeError("network"), True]
    asyncio.run(care.confirm_disease("record", "thread", True, user))
    assert row["status"] == "partial_failure"
    assert [r["status"] for r in row["data"]["results"]] == [
        "sent_unconfirmed",
        "failed",
        "unknown",
        "sent_unconfirmed",
    ]
    asyncio.run(care.confirm_disease("record", "thread", True, user))
    assert publish.await_count == 4


def test_invalid_detection_or_thread_is_rejected(setup, monkeypatch):
    user, _, _, publish = setup
    monkeypatch.setattr(
        care, "require_record", AsyncMock(return_value={"status": "failed", "data": {"task": "disease"}})
    )
    with pytest.raises(HTTPException):
        asyncio.run(care.analyze_disease("thread", ["d1"], None, user))
    monkeypatch.setattr(care, "require_thread", AsyncMock(side_effect=HTTPException(404)))
    with pytest.raises(HTTPException):
        asyncio.run(care.analyze_disease("thread", ["d1"], None, user))
    publish.assert_not_awaited()


def test_knowledge_is_actually_queried_and_permissions_enforced(setup, monkeypatch):
    user, _, _, publish = setup
    monkeypatch.setattr(
        care, "require_record", AsyncMock(return_value={"id": "d1", "status": "ready", "data": {"task": "disease"}})
    )
    knowledge = SimpleNamespace(
        check_accessible=AsyncMock(return_value=True), aquery=AsyncMock(return_value="evidence")
    )
    monkeypatch.setattr(care, "knowledge_base", knowledge)
    result = asyncio.run(care.analyze_disease("thread", ["d1"], "kb", user))
    assert result["data"]["tools"][-1]["result"] == "evidence"
    knowledge.aquery.assert_awaited_once()
    knowledge.check_accessible.return_value = False
    with pytest.raises(HTTPException):
        asyncio.run(care.analyze_disease("thread", ["d1"], "kb", user))
    publish.assert_not_awaited()
