import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from yuxi.services import field_analysis_service as service


@pytest.mark.parametrize("device_id", [None, "device-1"])
@pytest.mark.parametrize("selected_ids", [None, ["older", "newer"]])
def test_analysis_runs_once_outside_selection_loop(monkeypatch, device_id, selected_ids):
    user = SimpleNamespace(department_id=1)
    album = {"name": "album", "device_id": device_id}
    records = [
        {
            "id": record_id,
            "status": "ready",
            "created_at": f"2026-10-{day}T00:00:00+00:00",
            "data": {"task": "disease", "captured_at": f"2026-10-{day}T00:00:00+00:00"},
        }
        for record_id, day in [("older", "20"), ("newer", "21")]
    ]
    monkeypatch.setattr(service, "require_album", AsyncMock(return_value=album))
    listing = AsyncMock(return_value=records)
    creation = AsyncMock(return_value={"id": "analysis"})
    knowledge = AsyncMock(return_value={"status": "not_selected"})
    sensors = AsyncMock(return_value={"total": 1, "items": [{"temp": 20}]})
    monkeypatch.setattr(service.repo, "list", listing)
    monkeypatch.setattr(service.repo, "get", AsyncMock(side_effect=records))
    monkeypatch.setattr(service.repo, "create", creation)
    monkeypatch.setattr(service, "retrieve_knowledge", knowledge)
    monkeypatch.setattr(service.sensor_history_repository, "query", sensors)

    result = asyncio.run(service.analyze_album("album", None, None, user, selected_ids))

    assert result == {"id": "analysis"}
    listing.assert_awaited_once_with("detection", 1, parent_id="album", limit=1000)
    knowledge.assert_awaited_once_with(None, user)
    creation.assert_awaited_once()
    data = creation.call_args.kwargs["data"]
    assert data["latest_disease"]["id"] == "newer"
    assert data["estimate"]["status"] == "insufficient_data"
    assert data["selected_disease_records"] == (records if selected_ids else [])
    assert data["knowledge"] == {"status": "not_selected"}
    assert sensors.await_count == (1 if device_id else 0)
    assert data["sensor_history"]["total"] == (1 if device_id else 0)
