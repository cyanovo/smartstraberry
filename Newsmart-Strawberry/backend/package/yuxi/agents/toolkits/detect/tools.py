"""番茄成熟度检测工具 —— 让 Agent 可以调用摄像头进行成熟度检测"""

from typing import Annotated

from langchain_core.tools import InjectedToolCallId
from pydantic import BaseModel, Field

from yuxi.agents.toolkits.registry import tool
from yuxi.utils import logger


class CaptureAndDetectInput(BaseModel):
    """拍照检测输入"""

    zone: str = Field(default="A", description="棚区标识，可选: A, B, C")


@tool(
    category="buildin",
    tags=["检测", "成熟度", "摄像头", "番茄"],
    display_name="拍照检测成熟度",
    args_schema=CaptureAndDetectInput,
)
async def capture_and_detect(zone: str = "A") -> dict:
    """使用摄像头拍照并执行番茄成熟度检测。

    通过高清摄像头拍摄当前棚区画面，使用 YOLO 模型识别番茄的成熟状态（成熟/半成熟/未成熟），
    返回检测统计和采摘建议。

    Args:
        zone: 棚区标识 (A/B/C)

    Returns:
        dict: 检测结果，包含成熟度统计、采摘建议
    """
    try:
        from yuxi.services.detect_service import detect_service

        if not detect_service.is_ready:
            return {"error": "检测模型未就绪，请检查模型文件配置"}

        result = await detect_service.capture_and_detect(zone=zone)

        return {
            "棚区": zone,
            "检测总数": result.total_count,
            "成熟": result.ripe_count,
            "半成熟": result.half_ripe_count,
            "未成熟": result.unripe_count,
            "成熟度": f"{result.maturity_ratio}%",
            "建议": result.recommendation,
            "检测时间": result.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"拍照检测失败: {e}")
        return {"error": f"检测失败: {str(e)}"}


class GetDetectHistoryInput(BaseModel):
    """获取检测历史输入"""

    zone: str = Field(default="", description="棚区筛选，留空返回全部")
    limit: int = Field(default=10, description="返回数量")


@tool(
    category="buildin",
    tags=["检测", "历史", "成熟度"],
    display_name="获取检测历史",
    args_schema=GetDetectHistoryInput,
)
async def get_detect_history(zone: str = "", limit: int = 10) -> dict:
    """获取番茄成熟度检测的历史记录。

    返回最近的检测记录，包含检测时间、棚区、成熟度统计和建议。

    Args:
        zone: 棚区筛选 (A/B/C)，留空返回全部
        limit: 返回数量，默认 10

    Returns:
        dict: 检测历史列表
    """
    try:
        from yuxi.services.detect_service import detect_service

        records = await detect_service.get_history(
            zone=zone if zone else None,
            limit=limit,
        )

        history = []
        for r in records:
            history.append({
                "id": r.id,
                "棚区": r.zone,
                "检测总数": r.total_count,
                "成熟": r.ripe_count,
                "半成熟": r.half_ripe_count,
                "未成熟": r.unripe_count,
                "成熟度": f"{r.maturity_ratio}%",
                "建议": r.recommendation,
                "时间": r.created_at.isoformat(),
            })

        return {"记录数": len(history), "历史记录": history}

    except Exception as e:
        logger.error(f"获取检测历史失败: {e}")
        return {"error": f"查询失败: {str(e)}"}
