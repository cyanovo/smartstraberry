from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


# ---- 传感器数据模型 ----


class AirSensorData(BaseModel):
    """空气传感器数据（由 tomato_hnsw0001/telemetry 拆分得到）"""

    model_config = ConfigDict(populate_by_name=True)

    humidity: float = Field(..., validation_alias=AliasChoices("humidity", "air_humidity"), description="空气湿度（%）")
    temp: float = Field(..., validation_alias=AliasChoices("temp", "air_temperature"), description="空气温度（℃）")
    co2: int = Field(default=0, description="CO2 浓度（ppm，旧协议字段，新协议未提供时为 0）")
    illumination: float = Field(
        default=0,
        validation_alias=AliasChoices("illumination", "Illumination", "light_intensity"),
        serialization_alias="illumination",
        description="光照强度（lux）",
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="接收时间")


class SoilSensorData(BaseModel):
    """水培/根区传感器数据（由 tomato_hnsw0001/telemetry 拆分得到）"""

    model_config = ConfigDict(populate_by_name=True)

    soil_moisture: float = Field(default=0, description="土壤湿度（%，旧协议字段）")
    soil_temperature: float = Field(
        ...,
        validation_alias=AliasChoices("soil_temperature", "hydroponic_temperature"),
        description="水培/土壤温度（℃）",
    )
    soil_conductivity: float = Field(
        ..., validation_alias=AliasChoices("soil_conductivity", "ec"), description="EC（μS/cm）"
    )
    ph_value: float = Field(..., validation_alias=AliasChoices("ph_value", "ph"), description="pH 值")
    water_tank_level: float = Field(default=0, description="水箱水位（cm）")
    nitrogen: float = Field(default=0, description="氮含量（旧协议字段）")
    phosphorus: float = Field(default=0, description="磷含量（旧协议字段）")
    potassium: float = Field(default=0, description="钾含量（旧协议字段）")
    timestamp: datetime = Field(default_factory=datetime.now, description="接收时间")


# ---- 执行器指令模型 ----


class MqttSetCommand(BaseModel):
    """新版 MQTT 控制指令（发布到 tomato_hnsw0001/set）"""

    request_id: str
    cmd: Literal["01", "02", "03", "04", "05", "06", "07", "08", "09"]
    data: dict


class IrrigationCommand(BaseModel):
    """灌溉/水泵控制指令（兼容旧服务层，最终映射为 cmd 03）"""

    action: Literal["start", "stop"]


class LedCommand(BaseModel):
    """LED 补光灯控制指令（映射到 cmd 04 总灯开关）"""

    led1: Literal["on", "off"] | None = None
    led2: Literal["on", "off"] | None = None
    led3: Literal["on", "off"] | None = None
    led4: Literal["on", "off"] | None = None
    led5: Literal["on", "off"] | None = None


# ---- 聚合响应模型 ----


class ActuatorStatus(BaseModel):
    """执行器当前状态"""

    irrigation: bool | None = None  # 灌溉
    mist: bool = False  # 水雾培
    ventilation: bool | None = None  # 通风
    pump: bool | None = None  # 水泵
    ai_mode: bool = False  # AI 模式
    auto_mode: bool = True  # 手动模式（兼容旧响应字段名）
    red_brightness: int = 0
    blue_brightness: int = 0
    light_master_state: bool | None = None
    fill_light_mode: int | None = None
    pump_interval_min: int | None = None
    pump_duration_sec: int | None = None
    rest_schedule: dict | None = None
    leds: dict[str, bool] = Field(
        default_factory=lambda: {
            "led1": False,
            "led2": False,
            "led3": False,
            "led4": False,
            "led5": False,
        }
    )


class IotDashboardData(BaseModel):
    """IoT 仪表盘聚合数据 — 前端单次查询即可获取全部实时数据"""

    air: AirSensorData | None = None
    soil: SoilSensorData | None = None
    actuators: ActuatorStatus = Field(default_factory=ActuatorStatus)
    device_control: dict = Field(default_factory=dict)
