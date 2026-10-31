import json
from types import SimpleNamespace
from unittest.mock import patch

from yuxi.iot.schemas import AirSensorData, SoilSensorData, MqttSetCommand, LedCommand
from yuxi.iot.mqtt_client import MqttClient


class TestMqttClient:

    @patch.dict("os.environ", {"MQTT_ENABLED": "false"})
    def test_disabled_by_default(self):
        client = MqttClient()
        assert client.enabled is False

    @patch.dict("os.environ", {"MQTT_ENABLED": "true"})
    def test_enabled_when_configured(self):
        client = MqttClient()
        assert client.enabled is True

    def test_air_sensor_parsing(self):
        """验证空气传感器数据字段校验与别名映射"""
        payload = {"air_humidity": 45.5, "air_temperature": 25.3, "light_intensity": 12000}
        data = AirSensorData(**payload)
        assert data.humidity == 45.5
        assert data.temp == 25.3
        assert data.co2 == 0
        assert data.illumination == 12000

    def test_soil_sensor_parsing(self):
        """验证水培传感器字段解析"""
        payload = {
            "hydroponic_temperature": 23.8,
            "water_tank_level": 10.4,
            "ph": 6.8,
            "ec": 1200,
        }
        data = SoilSensorData(**payload)
        assert data.ph_value == 6.8
        assert data.soil_temperature == 23.8
        assert data.water_tank_level == 10.4
        assert data.soil_conductivity == 1200

    def test_mqtt_set_command(self):
        cmd = MqttSetCommand(request_id="phone-001", cmd="05", data={"value": 3})
        assert json.loads(cmd.model_dump_json()) == {
            "request_id": "phone-001",
            "cmd": "05",
            "data": {"value": 3},
        }

    @patch.dict("os.environ", {"MQTT_PROTOCOL": "tomato_v11"})
    def test_publish_pump_command(self):
        class FakeClient:
            def __init__(self):
                self.messages = []

            def is_connected(self):
                return True

            def publish(self, topic, payload, qos=0):
                self.messages.append((topic, json.loads(payload), qos))
                return SimpleNamespace(rc=0)

        client = MqttClient()
        fake = FakeClient()
        client._client = fake

        assert client.publish_pump(True) is True
        topic, payload, qos = fake.messages[0]
        assert topic == "tomato_hnsw0001/set"
        assert payload["cmd"] == "03"
        assert payload["data"] == {"value": 1}
        assert qos == 1

    @patch.dict("os.environ", {"MQTT_PROTOCOL": "tomato_v11"})
    def test_publish_v11_parameter_commands(self):
        class FakeClient:
            def __init__(self):
                self.messages = []

            def is_connected(self):
                return True

            def publish(self, topic, payload, qos=0):
                self.messages.append((topic, json.loads(payload), qos))
                return SimpleNamespace(rc=0)

        client = MqttClient()
        fake = FakeClient()
        client._client = fake

        assert client.publish_red_brightness(80) is True
        assert client.publish_blue_brightness(60) is True
        assert client.publish_fill_light_mode(3) is True
        assert client.publish_pump_interval(30) is True
        assert client.publish_pump_duration(20) is True
        assert client.publish_rest_schedule(20, 12, 7, 22) is True

        commands = [(payload["cmd"], payload["data"]) for _, payload, _ in fake.messages]
        assert commands == [
            ("01", {"value": 80}),
            ("02", {"value": 60}),
            ("05", {"value": 3}),
            ("06", {"value": 30}),
            ("07", {"value": 20}),
            ("09", {"start_hour": 20, "start_minute": 12, "end_hour": 7, "end_minute": 22}),
        ]

    def test_led_single_channel(self):
        """LED 指令只包含指定通道"""
        cmd = LedCommand(led3="on")
        payload = json.loads(cmd.model_dump_json(exclude_none=True))
        assert payload == {"led3": "on"}

    def test_led_multi_channel(self):
        """LED 指令可以同时控制多路"""
        cmd = LedCommand(led1="on", led2="on", led3="off")
        payload = json.loads(cmd.model_dump_json(exclude_none=True))
        assert payload == {"led1": "on", "led2": "on", "led3": "off"}

    def test_led_invalid_value_rejected(self):
        """非法值应被 Pydantic 拒绝"""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LedCommand(led1="invalid")
