"""检测相关数据模型"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """单个检测目标"""

    class_id: int = Field(..., description="类别 ID (0=成熟, 1=半成熟, 2=未成熟)")
    class_name: str = Field(..., description="类别名称")
    confidence: float = Field(..., description="置信度 0-1")
    box: list[int] = Field(..., description="边界框 [x1, y1, x2, y2]")


class DetectResult(BaseModel):
    """检测结果"""

    id: str = Field(..., description="记录 ID")
    zone: str = Field(..., description="棚区标识 (A/B/C)")
    camera_id: int = Field(default=0, description="摄像头 ID")
    total_count: int = Field(..., description="检测总数")
    ripe_count: int = Field(..., description="成熟数量")
    half_ripe_count: int = Field(..., description="半成熟数量")
    unripe_count: int = Field(..., description="未成熟数量")
    maturity_ratio: float = Field(..., description="成熟度百分比 0-100")
    confidence_threshold: float = Field(default=0.5, description="置信度阈值")
    detections: list[Detection] = Field(default_factory=list, description="详细检测结果")
    recommendation: str = Field(default="", description="采摘建议")
    annotated_image_base64: str = Field(default="", description="标注图片 base64")
    created_at: datetime = Field(default_factory=datetime.now, description="检测时间")


class CameraConfig(BaseModel):
    """摄像头配置"""

    camera_id: int = Field(default=0, description="摄像头 ID (0=内置, 1+=USB)")
    width: int = Field(default=1280, description="采集宽度")
    height: int = Field(default=720, description="采集高度")
    enabled: bool = Field(default=True, description="是否启用摄像头")


class DetectConfig(BaseModel):
    """检测配置"""

    confidence_threshold: float = Field(default=0.5, description="置信度阈值")
    model_path: str = Field(default="", description="模型路径")
    default_zone: str = Field(default="A", description="默认棚区")


# 成熟度类别映射
MATURITY_CLASSES: dict[int, str] = {
    0: "成熟",
    1: "半成熟",
    2: "未成熟",
}

# 类别颜色映射 (BGR)
CLASS_COLORS: dict[int, tuple[int, int, int]] = {
    0: (0, 0, 200),      # 红色 - 成熟
    1: (0, 200, 200),    # 黄色 - 半成熟
    2: (0, 200, 0),      # 绿色 - 未成熟
}
