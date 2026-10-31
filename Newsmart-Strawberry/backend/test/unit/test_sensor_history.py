import csv
import importlib.util
import io
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from server.utils.auth_middleware import get_required_user
from yuxi.iot.schemas import AirSensorData, SoilSensorData
from yuxi.services import sensor_history_service as service
from yuxi.services.iot_service import IotService


async def test_callback_persists_actual_fields_before_cache(monkeypatch):
    append = AsyncMock()
    monkeypatch.setattr(service.sensor_history_repository, "append", append)
    monkeypatch.setenv("MQTT_SENSOR_DEVICE_ID", "test-device")
    instance = IotService()
    instance._redis = AsyncMock()
    await instance.on_air_data(AirSensorData(temp=22, humidity=60))
    values = append.call_args.kwargs
    assert values["device_id"] == "test-device"
    assert values["values"] == {"temp": 22, "humidity": 60}
    assert values["sampled_at"].tzinfo is not None
    instance._redis.set.assert_awaited_once()


async def test_database_failure_is_not_silently_successful(monkeypatch):
    monkeypatch.setattr(service.sensor_history_repository, "append", AsyncMock(side_effect=RuntimeError("db offline")))
    instance = IotService()
    instance._redis = AsyncMock()
    with pytest.raises(RuntimeError, match="db offline"):
        await instance.on_air_data(AirSensorData(temp=22, humidity=60))
    instance._redis.set.assert_not_awaited()


async def test_soil_callback_preserves_only_reported_fields(monkeypatch):
    append = AsyncMock()
    monkeypatch.setattr(service.sensor_history_repository, "append", append)
    instance = IotService()
    instance._redis = AsyncMock()
    await instance.on_soil_data(SoilSensorData(soil_temperature=21, soil_conductivity=1100, ph_value=6.2))
    assert append.call_args.kwargs["kind"] == "soil"
    assert append.call_args.kwargs["values"] == {
        "soil_temperature": 21,
        "soil_conductivity": 1100,
        "ph_value": 6.2,
    }
    instance._redis.set.assert_awaited_once()


def test_csv_preserves_missing_values_and_neutralizes_formula():
    output = service.history_csv(
        [
            {
                "id": "1",
                "device_id": "=SUM(1,2)",
                "kind": "air",
                "sampled_at": "now",
                "received_at": "now",
                "values": {"temp": 0},
            }
        ]
    )
    row = next(csv.DictReader(io.StringIO(output.decode("utf-8-sig"))))
    assert row["device_id"].startswith("'")
    assert row["air_temperature_C"] == "0"
    assert row["co2_ppm"] == ""


def test_time_validation(monkeypatch):
    monkeypatch.setenv("SENSOR_TIMEZONE", "Asia/Shanghai")
    assert service.normalize_sample_time(datetime(2026, 10, 22, 8)).hour == 0
    with pytest.raises(ValueError, match="时区"):
        service.validate_range(datetime(2026, 10, 22), None)
    with pytest.raises(ValueError, match="开始"):
        service.validate_range(datetime(2026, 10, 23, tzinfo=UTC), datetime(2026, 10, 22, tzinfo=UTC))


async def test_history_routes_filter_validate_and_export(monkeypatch):
    path = Path(__file__).resolve().parents[2] / "server/routers/iot_router.py"
    spec = importlib.util.spec_from_file_location("sensor_history_test_router", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    query = AsyncMock(return_value={"total": 0, "items": []})
    monkeypatch.setattr(service.sensor_history_repository, "query", query)
    app = FastAPI()
    app.include_router(module.iot)
    app.dependency_overrides[get_required_user] = lambda: object()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.get(
            "/iot/history", params={"device_id": "test", "kind": "air", "limit": 20, "offset": 40}
        )
        assert result.json() == {"total": 0, "items": []}
        assert query.call_args.kwargs["offset"] == 40
        assert query.call_args.kwargs["device_id"] == "test"
        assert (await client.get("/iot/history?limit=0")).status_code == 422
        assert (await client.get("/iot/history?start=2026-10-22T00:00:00")).status_code == 400
        exported = await client.get("/iot/history/export")
        assert exported.status_code == 200
        assert "attachment" in exported.headers["content-disposition"]
        assert "air_temperature_C" in exported.text
        query.return_value = {"total": service.EXPORT_LIMIT + 1, "items": []}
        assert (await client.get("/iot/history/export")).status_code == 400
