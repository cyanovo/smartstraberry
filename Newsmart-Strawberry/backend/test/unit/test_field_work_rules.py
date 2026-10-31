import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from yuxi.services.field_analysis_service import estimate_visible
from yuxi.services.field_model_service import validate_classes
from yuxi.services.field_work_service import folder_name, require_manager


def test_estimate_uses_latest_capture_not_sum_or_latest_reprocessing():
    rows = [
        {"id": "older", "status": "ready", "created_at": "2026-10-23", "data": {
            "task": "maturity", "captured_at": "2026-10-20", "photo_id": "p1", "counts": {"Ripe": 50}}},
        {"id": "latest", "status": "ready", "created_at": "2026-10-22", "data": {
            "task": "maturity", "captured_at": "2026-10-22", "photo_id": "p2", "counts": {"Ripe": 3, "Unripe": 2}}},
    ]
    assert estimate_visible(rows)["visible_ripe_mass_g"] is None
    assert estimate_visible(rows, 20)["visible_ripe_mass_g"] == 60
    assert estimate_visible(rows)["visible_fruits"] == 5
    assert estimate_visible([])["status"] == "insufficient_data"


def test_model_classes_and_shared_path_permissions():
    assert validate_classes({0: "Ripe", 1: "Unripe", 2: "Half-ripe"}, "maturity")
    with pytest.raises(ValueError):
        validate_classes({0: "tomato"}, "maturity")
    for path in ("../secret", "a/../b", "C:/data", "a/./b"):
        with pytest.raises(HTTPException):
            folder_name(path)
    assert folder_name("training/labels") == "training/labels"
    with pytest.raises(HTTPException):
        require_manager(SimpleNamespace(role="user", uid="other"), {"owner_uid": "owner"})


def test_confirmation_is_scoped_expiring_atomic_and_never_claims_execution(monkeypatch):
    from yuxi.services import control_proposal_service as control
    user = SimpleNamespace(uid="owner", department_id=1)
    state = {"device_control": {"online": True, "broker_connected": True, "states": {"light": None}},
             "air": {"temp": 20}, "soil": None}
    row = {"id": "proposal", "owner_uid": "owner", "parent_id": "thread", "status": "pending",
           "data": {"key": "light", "value": True, "snapshot": state,
                    "expires_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat()}}
    monkeypatch.setattr(control, "require_thread", AsyncMock())
    monkeypatch.setattr(control, "require_record", AsyncMock(side_effect=lambda *a: dict(row)))
    monkeypatch.setattr(control.iot_service, "get_dashboard", AsyncMock(return_value=SimpleNamespace(model_dump=lambda **k: state)))
    publish = AsyncMock(return_value=True)
    monkeypatch.setattr(control.iot_service, "control_actuator", publish)

    async def change(_id, _dept, *, status, expected=None, data=None):
        if expected and row["status"] != expected:
            return False
        row["status"] = status
        if data:
            row["data"] = data
        return True

    monkeypatch.setattr(control.repo, "change", change)

    async def run():
        with pytest.raises(HTTPException):
            await control.confirm_control("proposal", "other-thread", True, user)
        assert publish.await_count == 0
        row["data"]["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        with pytest.raises(HTTPException):
            await control.confirm_control("proposal", "thread", True, user)
        assert row["status"] == "expired"
        row["status"] = "pending"
        row["data"]["expires_at"] = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
        offline = {**state, "device_control": {**state["device_control"], "online": False}}
        control.iot_service.get_dashboard.return_value = SimpleNamespace(model_dump=lambda **k: offline)
        with pytest.raises(HTTPException):
            await control.confirm_control("proposal", "thread", True, user)
        changed = {**state, "air": {"temp": 25}}
        control.iot_service.get_dashboard.return_value = SimpleNamespace(model_dump=lambda **k: changed)
        with pytest.raises(HTTPException):
            await control.confirm_control("proposal", "thread", True, user)
        assert publish.await_count == 0
        control.iot_service.get_dashboard.return_value = SimpleNamespace(model_dump=lambda **k: state)
        await control.confirm_control("proposal", "thread", False, user)
        assert row["status"] == "rejected" and publish.await_count == 0
        row["status"] = "pending"
        await asyncio.gather(control.confirm_control("proposal", "thread", True, user),
                             control.confirm_control("proposal", "thread", True, user))
        assert publish.await_count == 1
        assert row["status"] == "sent_unconfirmed"

    asyncio.run(run())
