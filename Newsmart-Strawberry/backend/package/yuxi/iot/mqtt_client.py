from __future__ import annotations

import asyncio
import json
import os
import time
from uuid import uuid4
from collections.abc import Callable, Awaitable
from typing import TYPE_CHECKING

from yuxi.iot.schemas import ActuatorStatus, AirSensorData, SoilSensorData, IrrigationCommand, MqttSetCommand
from yuxi.utils import logger

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

# ---- 默认配置 ----
BROKER_URL = os.environ.get("MQTT_BROKER_URL", "broker.emqx.io")
BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
BROKER_USERNAME = os.environ.get("MQTT_BROKER_USERNAME", "admin")
BROKER_PASSWORD = os.environ.get("MQTT_BROKER_PASSWORD", "admin123")
CLIENT_ID = f"yuxi-server-{int(time.time())}"
KEEPALIVE = 120

# 主题常量
TOPIC_ROOT = os.environ.get("MQTT_TOPIC_ROOT", "tomato_hnsw0001").strip().strip("/")
TOPIC_SET = f"{TOPIC_ROOT}/set"
TOPIC_RESULT = f"{TOPIC_ROOT}/result"
TOPIC_STATE = f"{TOPIC_ROOT}/state"
TOPIC_TELEMETRY = f"{TOPIC_ROOT}/telemetry"
TOPIC_AVAILABILITY = f"{TOPIC_ROOT}/availability"
LEGACY_TOPIC_AIR = "/air/post"
LEGACY_TOPIC_SOIL = "/soil/post"
STRAWBERRY_TOPICS = {
    "fertigation": "strawberry_fert",
    "rotation": "strawberry_rotate",
    "irrigation": "strawberry_irrigation",
    "ventilation": "strawberry_fan",
    "light": "strawberry_light",
}


class MqttClient:
    """Yuxi MQTT 客户端（单例），封装 paho-mqtt 异步操作"""

    def __init__(self):
        self._client: mqtt.Client | None = None
        self._air_callback: Callable[[AirSensorData], Awaitable[None]] | None = None
        self._soil_callback: Callable[[SoilSensorData], Awaitable[None]] | None = None
        self._state_callback: Callable[[ActuatorStatus], Awaitable[None]] | None = None
        self._enabled = os.environ.get("MQTT_ENABLED", "false").lower() in ("true", "1")
        self._event_loop = None
        self._connected = False
        self.protocol = os.environ.get("MQTT_PROTOCOL", "strawberry").strip()
        if self.protocol not in ("strawberry", "tomato_v11"):
            raise ValueError("MQTT_PROTOCOL must be strawberry or tomato_v11")
        self.last_seen = None
        self.health = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def connected(self) -> bool:
        return self._connected

    def register_air_handler(self, cb: Callable[[AirSensorData], Awaitable[None]]):
        """注册空气传感器数据处理回调"""
        self._air_callback = cb

    def register_soil_handler(self, cb: Callable[[SoilSensorData], Awaitable[None]]):
        """注册土壤传感器数据处理回调"""
        self._soil_callback = cb

    def register_state_handler(self, cb: Callable[[ActuatorStatus], Awaitable[None]]):
        """注册设备状态快照处理回调"""
        self._state_callback = cb

    # ---------- 连接管理 ----------

    def connect(self):
        if not self._enabled:
            logger.info("MQTT is disabled (MQTT_ENABLED != true), skipping connection")
            return

        import paho.mqtt.client as mqtt

        self._event_loop = asyncio.get_running_loop()

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=CLIENT_ID
        )
        self._client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        try:
            self._client.connect(BROKER_URL, BROKER_PORT, KEEPALIVE)
            self._client.loop_start()
            logger.info(f"MQTT client connected to {BROKER_URL}:{BROKER_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect MQTT broker: {e}")
            self._enabled = False

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._connected = False
            logger.info("MQTT client disconnected")

    # ---------- 订阅 ----------

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self._connected = True
            topics = [
                (TOPIC_RESULT, 1),
                (TOPIC_STATE, 1),
                (TOPIC_TELEMETRY, 0),
                (TOPIC_AVAILABILITY, 1),
                (LEGACY_TOPIC_AIR, 1),
                (LEGACY_TOPIC_SOIL, 1),
            ]
            if self.protocol == "strawberry":
                topics = [(LEGACY_TOPIC_AIR, 0), (LEGACY_TOPIC_SOIL, 0), ("strawberry_status", 0)]
            client.subscribe(topics)
            logger.info(f"MQTT subscribed: {', '.join(topic for topic, _ in topics)}")
        else:
            self._connected = False
            logger.error(f"MQTT connection failed with code: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self._connected = False
        if reason_code != 0:
            logger.warning(f"MQTT disconnected unexpectedly, reason_code={reason_code}")
        else:
            logger.info("MQTT disconnected cleanly")

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        logger.info(f"MQTT message received: topic={msg.topic}, payload_len={len(msg.payload)}")

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning(f"MQTT received invalid JSON on topic {msg.topic}: {msg.payload[:200]}")
            return

        if not isinstance(payload, dict):
            return
        if self.protocol == "strawberry":
            if msg.topic not in (LEGACY_TOPIC_AIR, LEGACY_TOPIC_SOIL, "strawberry_status"):
                return
            # Retained samples cannot prove the controller is still online.
            if getattr(msg, "retain", False):
                return
            try:
                if msg.topic == LEGACY_TOPIC_AIR:
                    AirSensorData(**payload)
                elif msg.topic == LEGACY_TOPIC_SOIL:
                    SoilSensorData(**payload)
                else:
                    if not all(payload.get(key) in ("000", "001") for key in ("air", "soil", "relay")):
                        return
                    self.health = {key: payload[key] for key in ("air", "soil", "relay")}
            except ValueError:
                return
            self.last_seen = time.time()
            if msg.topic == "strawberry_status":
                return

        if msg.topic == TOPIC_TELEMETRY:
            asyncio.run_coroutine_threadsafe(self._handle_telemetry(payload), self._event_loop)
        elif msg.topic == TOPIC_STATE and self._state_callback:
            asyncio.run_coroutine_threadsafe(self._handle_state(payload), self._event_loop)
        elif msg.topic == TOPIC_RESULT:
            logger.info(f"MQTT command result: {payload}")
        elif msg.topic == TOPIC_AVAILABILITY:
            logger.info(f"MQTT device availability: {payload}")
        elif msg.topic == LEGACY_TOPIC_AIR and self._air_callback:
            asyncio.run_coroutine_threadsafe(self._handle_air(payload), self._event_loop)
        elif msg.topic == LEGACY_TOPIC_SOIL and self._soil_callback:
            asyncio.run_coroutine_threadsafe(self._handle_soil(payload), self._event_loop)
        else:
            logger.debug(f"MQTT message ignored on topic: {msg.topic}")

    async def _handle_telemetry(self, payload: dict):
        try:
            air_data = AirSensorData(**payload)
            soil_data = SoilSensorData(**payload)
            if self._air_callback:
                await self._air_callback(air_data)
            if self._soil_callback:
                await self._soil_callback(soil_data)
        except Exception as e:
            logger.error(f"Failed to handle telemetry data: {e}")

    async def _handle_state(self, payload: dict):
        try:
            data = ActuatorStatus(
                pump=bool(payload.get("pump_state", False)),
                irrigation=bool(payload.get("pump_state", False)),
                ai_mode=payload.get("control_mode") == 1,
                auto_mode=payload.get("control_mode") == 0,
                red_brightness=int(payload.get("red_brightness", 0)),
                blue_brightness=int(payload.get("blue_brightness", 0)),
                light_master_state=bool(payload.get("light_master_state", False)),
                fill_light_mode=payload.get("fill_light_mode"),
                pump_interval_min=payload.get("pump_interval_min"),
                pump_duration_sec=payload.get("pump_duration_sec"),
                rest_schedule=payload.get("rest_schedule"),
            )
            if self._state_callback:
                await self._state_callback(data)
        except Exception as e:
            logger.error(f"Failed to handle state data: {e}")

    async def _handle_air(self, payload: dict):
        try:
            data = AirSensorData(**payload)
            if self._air_callback:
                await self._air_callback(data)
        except Exception as e:
            logger.error(f"Failed to handle air sensor data: {e}")

    async def _handle_soil(self, payload: dict):
        try:
            data = SoilSensorData(**payload)
            if self._soil_callback:
                await self._soil_callback(data)
        except Exception as e:
            logger.error(f"Failed to handle soil sensor data: {e}")

    # ---------- 发布（控制指令）----------

    def publish_irrigation(self, cmd: IrrigationCommand) -> bool:
        return self.publish_pump(cmd.action == "start")

    def publish_set_command(self, cmd: str, data: dict, request_id: str | None = None) -> bool:
        if self.protocol == "strawberry":
            raise ValueError("当前草莓固件不支持调光、定时或自动模式指令")
        if not self._client or not self._client.is_connected():
            logger.warning(f"MQTT not connected, cannot publish command {cmd}")
            return False
        command = MqttSetCommand(
            request_id=request_id or f"server-{int(time.time())}-{uuid4().hex[:8]}",
            cmd=cmd,
            data=data,
        )
        payload = command.model_dump_json()
        result = self._client.publish(TOPIC_SET, payload, qos=1)
        if result.rc != 0:
            return False
        logger.info(f"Published to {TOPIC_SET}: {payload}")
        return True

    def publish_ventilation(self, action: str) -> bool:
        if self.protocol == "strawberry":
            if action not in ("start", "stop"):
                raise ValueError("action must be start or stop")
            return self.publish_relay("ventilation", action == "start")
        logger.warning("Ventilation command is not defined in MQTT protocol v1.1")
        return False

    def publish_mist(self, action: str) -> bool:
        logger.warning("Mist command is not defined in MQTT protocol v1.1")
        return False

    def publish_pump(self, enabled: bool) -> bool:
        if self.protocol == "strawberry":
            return self.publish_relay("irrigation", enabled)
        return self.publish_set_command("03", {"value": 1 if enabled else 0})

    def publish_light_master(self, enabled: bool) -> bool:
        if self.protocol == "strawberry":
            return self.publish_relay("light", enabled)
        return self.publish_set_command("04", {"value": 1 if enabled else 0})

    def publish_red_brightness(self, value: int) -> bool:
        return self.publish_set_command("01", {"value": value})

    def publish_blue_brightness(self, value: int) -> bool:
        return self.publish_set_command("02", {"value": value})

    def publish_fill_light_mode(self, value: int) -> bool:
        return self.publish_set_command("05", {"value": value})

    def publish_pump_interval(self, minutes: int) -> bool:
        return self.publish_set_command("06", {"value": minutes})

    def publish_pump_duration(self, seconds: int) -> bool:
        return self.publish_set_command("07", {"value": seconds})

    def publish_rest_schedule(self, start_hour: int, start_minute: int, end_hour: int, end_minute: int) -> bool:
        return self.publish_set_command(
            "09",
            {
                "start_hour": start_hour,
                "start_minute": start_minute,
                "end_hour": end_hour,
                "end_minute": end_minute,
            },
        )

    def publish_mode(self, mode: str) -> bool:
        return self.publish_set_command("08", {"value": 1 if mode == "ai" else 0})

    def publish_relay(self, key: str, enabled: bool) -> bool:
        if self.protocol != "strawberry" or key not in STRAWBERRY_TOPICS:
            raise ValueError("当前协议不支持该执行器")
        if not self._client or not self._client.is_connected():
            return False
        # No retained commands or offline queue: a reconnect must not replay a start.
        result = self._client.publish(
            STRAWBERRY_TOPICS[key], json.dumps({"action": "start" if enabled else "stop"}),
            qos=0, retain=False,
        )
        return result.rc == 0


# 模块级单例
mqtt_client = MqttClient()
