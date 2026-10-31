import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import importlib.util
from pathlib import Path

from server.utils.auth_middleware import get_required_user
from yuxi.iot.mqtt_client import MqttClient, STRAWBERRY_TOPICS
from yuxi.services import iot_service as service_module

spec = importlib.util.spec_from_file_location(
    "iot_router_under_test", Path(__file__).resolve().parents[2] / "server/routers/iot_router.py"
)
router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router_module)
iot = router_module.iot


@pytest.fixture
def mqtt(monkeypatch):
    monkeypatch.setenv("MQTT_PROTOCOL", "strawberry")
    client = MqttClient()
    client._client = Mock()
    client._client.is_connected.return_value = True
    client._client.publish.return_value = SimpleNamespace(rc=0)
    monkeypatch.setattr(service_module, "mqtt_client", client)
    return client


@pytest.mark.parametrize("key,topic", STRAWBERRY_TOPICS.items())
@pytest.mark.parametrize("enabled", [True, False])
def test_five_relay_topics_and_payloads(mqtt, key, topic, enabled):
    assert mqtt.publish_relay(key, enabled)
    args, kwargs = mqtt._client.publish.call_args
    assert args[0] == topic
    assert json.loads(args[1]) == {"action": "start" if enabled else "stop"}
    assert kwargs == {"qos": 0, "retain": False}


def test_offline_and_rejected_publish_are_failures(mqtt):
    mqtt._client.is_connected.return_value = False
    assert not mqtt.publish_relay("light", True)
    mqtt._client.publish.assert_not_called()
    mqtt._client.is_connected.return_value = True
    mqtt._client.publish.return_value.rc = 4
    assert not mqtt.publish_relay("light", False)


def test_unsupported_commands_do_not_publish(mqtt):
    with pytest.raises(ValueError):
        mqtt.publish_relay("mist", True)
    with pytest.raises(ValueError):
        mqtt.publish_red_brightness(50)
    mqtt._client.publish.assert_not_called()


@pytest.mark.parametrize("payload,retained,valid", [
    (b'{"air":"001","soil":"000","relay":"001"}', False, True),
    (b'{"air":"001","soil":"000","relay":"001"}', True, False),
    (b'[]', False, False), (b'{}', False, False), (b'\xff', False, False),
])
def test_only_live_valid_status_proves_recent_activity(mqtt, payload, retained, valid):
    mqtt._on_message(None, None, SimpleNamespace(topic="strawberry_status", payload=payload, retain=retained))
    assert (mqtt.last_seen is not None) == valid
    assert not hasattr(mqtt, "relay_state")


@pytest.mark.asyncio
async def test_commands_never_persist_an_assumed_hardware_state(mqtt):
    service = service_module.IotService()
    service._redis = AsyncMock()
    assert await service.control_actuator("pump", True)
    assert await service.start_irrigation()
    assert await service.stop_irrigation()
    service._redis.set.assert_not_called()
    assert (await service.get_actuator_status()).pump is None


@pytest.mark.asyncio
@pytest.mark.parametrize("age,connected,online", [(0, True, True), (36, True, False), (0, False, False)])
async def test_dashboard_freshness_and_unknown_state(mqtt, age, connected, online):
    service = service_module.IotService()
    service._redis = AsyncMock()
    service._redis.get.return_value = None
    mqtt.last_seen = time.time() - age
    mqtt._connected = connected
    result = await service.get_dashboard()
    assert result.device_control["online"] is online
    assert result.device_control["states"] == dict.fromkeys(STRAWBERRY_TOPICS)
    assert result.actuators.pump is None


@pytest.fixture
def api(mqtt, monkeypatch):
    import importlib
    module = importlib.import_module("yuxi.iot.mqtt_client")
    monkeypatch.setattr(module, "mqtt_client", mqtt)
    app = FastAPI()
    app.include_router(iot, prefix="/api")
    app.dependency_overrides[get_required_user] = lambda: SimpleNamespace(id=1)
    return TestClient(app)


def test_api_sends_but_does_not_confirm_execution(api, mqtt):
    response = api.post("/api/iot/actuators/ventilation?value=true")
    assert response.status_code == 200
    assert response.json()["status"] == "sent_unconfirmed"
    assert mqtt._client.publish.call_args.args[0] == "strawberry_fan"


@pytest.mark.parametrize("path", [
    "/actuators/mist?value=true", "/light/red?value=50", "/mode?mode=ai",
    "/pump/duration?value=20", "/actuators/led",
])
def test_api_rejects_unsupported_hardware_features(api, mqtt, path):
    assert api.post("/api/iot" + path).status_code == 400
    mqtt._client.publish.assert_not_called()


def test_api_publish_failure(api, mqtt):
    mqtt._client.publish.return_value.rc = 4
    assert api.post("/api/iot/actuators/light?value=false").status_code == 503


def test_api_requires_authentication(mqtt):
    app = FastAPI()
    app.include_router(iot, prefix="/api")
    with TestClient(app) as client:
        assert client.post("/api/iot/actuators/light?value=true").status_code in (401, 403)
    mqtt._client.publish.assert_not_called()
