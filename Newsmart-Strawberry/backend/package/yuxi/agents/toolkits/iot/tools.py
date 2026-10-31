"""IoT 工具模块 —— 让 Agent 可以读取温室传感器和执行器数据"""

from pydantic import BaseModel, Field
from langgraph.prebuilt.tool_node import ToolRuntime

from yuxi.agents.toolkits.registry import tool
from yuxi.utils import logger


class GetDashboardInput(BaseModel):
    """获取仪表盘聚合数据"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "传感器", "温室"],
    display_name="获取温室仪表盘数据",
    args_schema=GetDashboardInput,
)
async def get_iot_dashboard(dummy: str = "") -> dict:
    """获取温室 IoT 仪表盘聚合数据，包含空气传感器、土壤传感器和执行器状态。

    这是最常用的查询方式，一次调用获取所有实时数据。
    返回 JSON 包含 air（温湿度/光照）、soil（水培温度/水位/pH/EC）、actuators（水泵/补光/模式状态）。

    Returns:
        dict: 聚合仪表盘数据，各字段可能为 null（传感器离线时）
    """
    try:
        from yuxi.services.iot_service import iot_service

        dashboard = await iot_service.get_dashboard()
        if dashboard is None:
            return {"error": "无法获取仪表盘数据"}

        result = {"air": None, "soil": None, "actuators": None}

        if dashboard.air:
            result["air"] = {
                "温度_℃": dashboard.air.temp,
                "湿度_%": dashboard.air.humidity,
                "光照_lx": dashboard.air.illumination,
                "采集时间": dashboard.air.timestamp.isoformat() if dashboard.air.timestamp else "",
            }

        if dashboard.soil:
            result["soil"] = {
                "水培温度_℃": dashboard.soil.soil_temperature,
                "水箱水位_cm": dashboard.soil.water_tank_level,
                "EC_uS_cm": dashboard.soil.soil_conductivity,
                "pH值": dashboard.soil.ph_value,
                "采集时间": dashboard.soil.timestamp.isoformat() if dashboard.soil.timestamp else "",
            }

        if dashboard.actuators:
            result["actuators"] = {
                "灌溉": "开启" if dashboard.actuators.irrigation else "关闭",
                "水泵": "开启" if dashboard.actuators.pump else "关闭",
                "AI模式": "开启" if dashboard.actuators.ai_mode else "关闭",
                "手动模式": "开启" if dashboard.actuators.auto_mode else "关闭",
                "红光亮度": dashboard.actuators.red_brightness,
                "蓝光亮度": dashboard.actuators.blue_brightness,
                "补光模式": dashboard.actuators.fill_light_mode,
                "LED灯": {k: "开启" if v else "关闭" for k, v in dashboard.actuators.leds.items()},
            }

        result["device_control"] = dashboard.device_control
        if dashboard.device_control.get("protocol") == "strawberry":
            result["actuators"] = {key: "未知（无硬件回执）" for key in dashboard.device_control.get("states", {})}
        return result

    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        return {"error": f"获取数据失败: {str(e)}"}


class GetAirSensorsInput(BaseModel):
    """获取空气传感器数据"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "传感器", "空气"],
    display_name="获取空气传感器数据",
    args_schema=GetAirSensorsInput,
)
async def get_air_sensors(dummy: str = "") -> dict:
    """获取温室空气传感器最新数据：温度、湿度、光照强度。

    Returns:
        dict: 空气传感器读数，包含温度(°C)、湿度(%)、光照(lx)和采集时间
    """
    try:
        from yuxi.services.iot_service import iot_service

        data = await iot_service.get_latest_air()
        if data is None:
            return {"error": "空气传感器离线，暂无数据"}

        return {
            "温度_℃": data.temp,
            "湿度_%": data.humidity,
            "光照_lx": data.illumination,
            "采集时间": data.timestamp.isoformat() if data.timestamp else "",
        }

    except Exception as e:
        logger.error(f"获取空气传感器失败: {e}")
        return {"error": f"获取失败: {str(e)}"}


class GetSoilSensorsInput(BaseModel):
    """获取土壤传感器数据"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "传感器", "土壤"],
    display_name="获取土壤传感器数据",
    args_schema=GetSoilSensorsInput,
)
async def get_soil_sensors(dummy: str = "") -> dict:
    """获取温室水培传感器最新数据：pH值、EC、水温、水箱水位。

    Returns:
        dict: 土壤传感器读数
    """
    try:
        from yuxi.services.iot_service import iot_service

        data = await iot_service.get_latest_soil()
        if data is None:
            return {"error": "土壤传感器离线，暂无数据"}

        return {
            "水培温度_℃": data.soil_temperature,
            "水箱水位_cm": data.water_tank_level,
            "EC_uS_cm": data.soil_conductivity,
            "pH值": data.ph_value,
            "采集时间": data.timestamp.isoformat() if data.timestamp else "",
        }

    except Exception as e:
        logger.error(f"获取土壤传感器失败: {e}")
        return {"error": f"获取失败: {str(e)}"}


# ---------- 执行器控制工具 ----------

CONTROL_KEYS = ["irrigation", "pump", "fertigation", "rotation", "ventilation", "light"]


class ControlActuatorInput(BaseModel):
    """执行器控制输入"""

    key: str = Field(description=f"执行器名称，可选: {', '.join(CONTROL_KEYS)}")
    value: bool = Field(description="true=开启, false=关闭")


@tool(
    category="buildin",
    tags=["IoT", "执行器", "控制"],
    display_name="控制执行器开关",
    args_schema=ControlActuatorInput,
)
async def control_actuator(key: str, value: bool, runtime: ToolRuntime) -> dict:
    """生成执行器开关建议，不发送指令。用户必须在当前对话设备建议面板明确确认。

    使用前必须先通过 get_iot_dashboard 或 get_actuators 确认当前状态，
    结合传感器数据判断是否需要操作。

    Args:
        key: 执行器名称（irrigation/pump）
        value: true=开启, false=关闭

    Returns:
        dict: {"ok": true/false, "key": "...", "value": true/false, "message": "..."}
    """
    if key not in CONTROL_KEYS:
        return {"ok": False, "key": key, "message": f"未知执行器，可选: {', '.join(CONTROL_KEYS)}"}

    try:
        from yuxi.repositories.user_repository import UserRepository
        from yuxi.services.control_proposal_service import propose_control

        user = await UserRepository().get_by_uid(str(runtime.context.uid))
        if not user or not user.department_id:
            return {"error": "用户无效"}
        thread_id = getattr(runtime.context, "thread_id", None) or runtime.config.get("configurable", {}).get(
            "thread_id"
        )
        row = await propose_control(thread_id, key, value, f"智能体建议{'开启' if value else '关闭'} {key}", user)
        return {"proposal_id": row["id"], "status": "pending", "message": row["data"]["message"]}
    except Exception as e:
        logger.error(f"控制执行器失败: {e}")
        return {"ok": False, "key": key, "message": f"控制失败: {str(e)}"}


class SetIotModeInput(BaseModel):
    """模式切换输入"""

    mode: str = Field(description="目标模式: manual(手动模式) 或 ai(AI模式)")


@tool(
    category="buildin",
    tags=["IoT", "模式", "控制"],
    display_name="切换IoT工作模式",
    args_schema=SetIotModeInput,
)
async def set_iot_mode(mode: str) -> dict:
    """切换温室 IoT 系统的工作模式。

    - manual: 手动模式，可直接控制灯光和水泵
    - ai: AI 模式，由AI根据实时数据分析决策

    Args:
        mode: "auto" 或 "ai"

    Returns:
        dict: {"ok": true/false, "mode": "...", "message": "..."}
    """
    return {"ok": False, "message": "智能体不得直接切换模式，请使用人工设备控制页面"}


class GetActuatorsInput(BaseModel):
    """获取执行器状态"""

    dummy: str = Field(default="", description="忽略")


@tool(
    category="buildin",
    tags=["IoT", "执行器", "控制"],
    display_name="获取执行器状态",
    args_schema=GetActuatorsInput,
)
async def get_actuators(dummy: str = "") -> dict:
    """获取温室执行器（水泵/补光/模式）的当前开关状态。

    Returns:
        dict: 各执行器的开启/关闭状态
    """
    try:
        from yuxi.services.iot_service import iot_service

        dashboard = await iot_service.get_dashboard()
        if dashboard.device_control.get("protocol") == "strawberry":
            return {"device_control": dashboard.device_control, "message": "固件无执行器状态回执，开关状态未知"}
        data = await iot_service.get_actuator_status()
        if data is None:
            return {"error": "无法获取执行器状态"}

        return {
            "灌溉": "开启" if data.irrigation else "关闭",
            "水泵": "开启" if data.pump else "关闭",
            "AI模式": "开启" if data.ai_mode else "关闭",
            "手动模式": "开启" if data.auto_mode else "关闭",
            "红光亮度": data.red_brightness,
            "蓝光亮度": data.blue_brightness,
            "补光模式": data.fill_light_mode,
            "LED灯": {k: "开启" if v else "关闭" for k, v in data.leds.items()},
        }

    except Exception as e:
        logger.error(f"获取执行器状态失败: {e}")
        return {"error": f"获取失败: {str(e)}"}
