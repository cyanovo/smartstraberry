from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from yuxi.services import field_analysis_service as service


@pytest.mark.asyncio
async def test_selected_disease_preserves_source_and_deduplicates(monkeypatch):
    user = SimpleNamespace(department_id=1)
    row = {"id": "d1", "parent_id": "other-album", "status": "ready", "data": {"task": "disease"}}
    monkeypatch.setattr(service, "require_album", AsyncMock(return_value={"name": "A", "device_id": ""}))
    monkeypatch.setattr(service.repo, "get", AsyncMock(return_value=row))
    monkeypatch.setattr(service.repo, "list", AsyncMock(return_value=[]))
    monkeypatch.setattr(service.repo, "create", AsyncMock(side_effect=lambda *a, **kw: kw["data"]))
    result = await service.analyze_album("a", None, None, user, ["d1", "d1"])
    assert result["selected_disease_records"] == [row]
    assert result["disease_evidence_source"] == "user_selected"
    assert result["estimate"]["status"] == "insufficient_data"
    service.repo.get.assert_awaited_once_with("d1", 1, "detection")


@pytest.mark.asyncio
@pytest.mark.parametrize("row,code", [
    (None, 404),
    ({"status": "failed", "data": {"task": "disease"}}, 422),
    ({"status": "ready", "data": {"task": "maturity"}}, 422),
])
async def test_rejects_inaccessible_or_invalid_disease(monkeypatch, row, code):
    monkeypatch.setattr(service, "require_album", AsyncMock(return_value={}))
    monkeypatch.setattr(service.repo, "get", AsyncMock(return_value=row))
    with pytest.raises(HTTPException) as exc:
        await service.analyze_album("a", None, None, SimpleNamespace(department_id=2), ["d1"])
    assert exc.value.status_code == code
