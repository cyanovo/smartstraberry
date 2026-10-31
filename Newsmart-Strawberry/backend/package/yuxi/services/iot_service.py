from __future__ import annotations

import asyncio
import json
import time

from yuxi.iot.mqtt_client import STRAWBERRY_TOPICS, mqtt_client
from yuxi.iot.schemas import (
    ActuatorStatus,
    AirSensorData,
    IotDashboardData,
    IrrigationCommand,
    LedCommand,
    SoilSensorData,
)
from yuxi.services.run_queue_service import get_redis_client
from yuxi.utils import logger


class IotService:
    """IoT 业务服务（单例 — 由 lifespan 初始化回调）"""

    KEY_AIR = "iot:latest:air"
    KEY_SOIL = "iot:latest:soil"
    KEY_ACTUATORS = "iot:actuators"

    def __init__(self):
        self._redis = None

    async def _ensure_redis(self):
        if self._redis is None:
            self._redis = await get_redis_client()

    # ---------- 传感器数据处理（MQTT 回调）----------

    async def on_air_data(self, data: AirSensorData):
        from yuxi.services.sensor_history_service import persist_sample

        await persist_sample("air", data)
        await self._ensure_redis()
        await self._redis.set(self.KEY_AIR, data.model_dump_json())
        logger.debug(f"Air sensor data updated: {data.temp}°C, {data.humidity}%")

    async def on_soil_data(self, data: SoilSensorData):
        from yuxi.services.sensor_history_service import persist_sample

        await persist_sample("soil", data)
        await self._ensure_redis()
        await self._redis.set(self.KEY_SOIL, data.model_dump_json())
        logger.debug(f"Hydroponic sensor data updated: ph={data.ph_value}, ec={data.soil_conductivity}")

    async def on_state_data(self, data: ActuatorStatus):
        await self._ensure_redis()
        await self._redis.set(self.KEY_ACTUATORS, data.model_dump_json())
        logger.debug(f"IoT actuator state updated: {data.model_dump_json()}")

    # ---------- 数据查询 ----------

    async def get_latest_air(self) -> AirSensorData | None:
        await self._ensure_redis()
        raw = await self._redis.get(self.KEY_AIR)
        if not raw:
            logger.debug(f"No air sensor data in Redis (key={self.KEY_AIR})")
            return None
        try:
            data = AirSensorData(**json.loads(raw))
            logger.debug(f"Air sensor data loaded: {data.temp}°C, {data.humidity}%")
            return data
        except Exception as e:
            logger.error(f"Failed to parse air sensor data from Redis (raw={raw[:200]}): {e}")
            return None

    async def get_latest_soil(self) -> SoilSensorData | None:
        await self._ensure_redis()
        raw = await self._redis.get(self.KEY_SOIL)
        if not raw:
            logger.debug(f"No soil sensor data in Redis (key={self.KEY_SOIL})")
            return None
        try:
            data = SoilSensorData(**json.loads(raw))
            logger.debug(f"Soil sensor data loaded: moisture={data.soil_moisture}%")
            return data
        except Exception as e:
            logger.error(f"Failed to parse soil sensor data from Redis (raw={raw[:200]}): {e}")
            return None

    async def get_actuator_status(self) -> ActuatorStatus:
        if mqtt_client.protocol == "strawberry":
            return ActuatorStatus()
        await self._ensure_redis()
        raw = await self._redis.get(self.KEY_ACTUATORS)
        if raw:
            return ActuatorStatus(**json.loads(raw))
        return ActuatorStatus()

    async def get_dashboard(self) -> IotDashboardData:
        air, soil, actuators = await asyncio.gather(
            self.get_latest_air(),
            self.get_latest_soil(),
            self.get_actuator_status(),
        )
        if mqtt_client.protocol == "strawberry":
            # Do not expose old optimistic actuator cache as hardware feedback.
            actuators = ActuatorStatus()
        dashboard = IotDashboardData(
            air=air, soil=soil, actuators=actuators,
            device_control={
                "protocol": mqtt_client.protocol,
                "broker_connected": mqtt_client.connected,
                "online": bool(mqtt_client.connected and mqtt_client.last_seen is not None
                               and time.time() - mqtt_client.last_seen < 35),
                "last_seen": mqtt_client.last_seen,
                "reported_health": mqtt_client.health,
                "feedback_supported": False if mqtt_client.protocol == "strawberry" else True,
                "states": {key: None for key in STRAWBERRY_TOPICS},
            },
        )
        logger.debug(
            f"IoT dashboard: air={'present' if air else 'missing'}, "
            f"soil={'present' if soil else 'missing'}, "
            f"actuators={actuators.model_dump_json()}"
        )
        return dashboard

    # ---------- 执行器控制 ----------

    async def start_irrigation(self) -> bool:
        ok = mqtt_client.publish_irrigation(IrrigationCommand(action="start"))
        if ok and mqtt_client.protocol != "strawberry":
            await self._update_actuator("irrigation", True)
            await self._update_actuator("pump", True)
        return ok



    async def stop_irrigation(self) -> bool:
        ok = mqtt_client.publish_irrigation(IrrigationCommand(action="stop"))
        if ok and mqtt_client.protocol != "strawberry":
            await self._update_actuator("irrigation", False)
            await self._update_actuator("pump", False)
        return ok

    async def control_actuator(self, key: str, value: bool) -> bool:
        """通用执行器控制 — 用于前端 Switch"""
        if mqtt_client.protocol == "strawberry":
            key = "irrigation" if key == "pump" else key
            return mqtt_client.publish_relay(key, value)
        match key:
            case "irrigation":
                return await (self.start_irrigation() if value else self.stop_irrigation())
            case "pump":
                if value:
                    return await self.start_irrigation()
                else:
                    return await self.stop_irrigation()
            case "mist":
                logger.warning("mist is not defined in MQTT protocol v1.1")
                return False
            case "ventilation":
                logger.warning("ventilation is

    # ---------- 模式控制 ----------

    async def set_mode(self, mode: str) -> bool:
        """设置工作模式 — AI 和自主互斥，通过 MQTT 下发到硬件"""
        if mode == "auto":
            mode = "manual"
        ok = mqtt_client.publish_mode(mode)
        if ok:
            current = await self.get_actuator_status()
            current.ai_mode = (mode == "ai")
            current.auto_mode = (mode == "manual")
            await self._redis.set(self.KEY_ACTUATORS, current.model_dump_json())
        return ok

    async def set_red_brightness(self, value: int) -> bool:
        ok = mqtt_client.publish_red_brightness(value)
        if ok:
            status = await self.get_actuator_status()
            status.red_brightness = value
            status.light_master_state = value > 0 or status.blue_brightness > 0
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def set_blue_brightness(self, value: int) -> bool:
        ok = mqtt_client.publish_blue_brightness(value)
        if ok:
            status = await self.get_actuator_status()
            status.blue_brightness = value
            status.light_master_state = status.red_brightness > 0 or value > 0
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def set_fill_light_mode(self, value: int) -> bool:
        ok = mqtt_client.publish_fill_light_mode(value)
        if ok:
            status = await self.get_actuator_status()
            status.fill_light_mode = value
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def set_pump_interval(self, minutes: int) -> bool:
        ok = mqtt_client.publish_pump_interval(minutes)
        if ok:
            status = await self.get_actuator_status()
            status.pump_interval_min = minutes
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def set_pump_duration(self, seconds: int) -> bool:
        ok = mqtt_client.publish_pump_duration(seconds)
        if ok:
            status = await self.get_actuator_status()
            status.pump_duration_sec = seconds
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def set_rest_schedule(self, start_hour: int, start_minute: int, end_hour: int, end_minute: int) -> bool:
        ok = mqtt_client.publish_rest_schedule(start_hour, start_minute, end_hour, end_minute)
        if ok:
            status = await self.get_actuator_status()
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            status.rest_schedule = {
                "start_hour": start_hour,
                "start_minute": start_minute,
                "end_hour": end_hour,
                "end_minute": end_minute,
                "crosses_midnight": end_minutes < start_minutes,
            }
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def control_led(self, cmd: LedCommand) -> bool:
        """控制补光灯；旧的多路 LED 接口映射到新版总灯开关。"""
        if mqtt_client.protocol == "strawberry":
            raise ValueError("当前固件只有一路补光灯，请使用 light 执行器")
        values = [getattr(cmd, led_name, None) for led_name in ("led1", "led2", "led3", "led4", "led5")]
        selected = [value for value in values if value is not None]
        if not selected:
            return False

        ok = mqtt_client.publish_light_master(any(value == "on" for value in selected))
        if ok:
            await self._persist_led_state(cmd)
            status = await self.get_actuator_status()
            status.light_master_state = any(value == "on" for value in status.leds.values())
            await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())
        return ok

    async def _update_actuator(self, key: str, value: bool):
        await self._ensure_redis()
        status = await self.get_actuator_status()
        setattr(status, key, value)
        await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())

    async def _persist_led_state(self, cmd: LedCommand):
        await self._ensure_redis()
        status = await self.get_actuator_status()
        for led_name in ("led1", "led2", "led3", "led4", "led5"):
            val = getattr(cmd, led_name, None)
            if val is not None:
                status.leds[led_name] = val == "on"
        await self._redis.set(self.KEY_ACTUATORS, status.model_dump_json())


# 模块级单例
iot_service = IotService()
