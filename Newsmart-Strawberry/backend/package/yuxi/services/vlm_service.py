"""大模型视觉识别服务 —— 基于 Qwen3-VL-Plus

提供番茄成熟度评估、目标检测、种植建议、病虫害识别功能。
使用 DashScope OpenAI 兼容接口调用 Qwen3-VL-Plus 视觉语言模型。
"""

from __future__ import annotations

import base64
import io
import json
import os
import re

import cv2
import numpy as np
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

from yuxi.utils import logger


class VlmDetection(BaseModel):
    """单个检测目标"""

    class_name: str = Field(..., description="类别：成熟/半成熟/未成熟")
    confidence: float = Field(default=0.9, description="置信度")
    box: list[int] = Field(..., description="边界框 [x1, y1, x2, y2]")


class VlmAnalysisResult(BaseModel):
    """大模型视觉分析结果"""

    total_count: int = Field(default=0, description="检测总数")
    ripe_count: int = Field(default=0, description="成熟数量")
    half_ripe_count: int = Field(default=0, description="半成熟数量")
    unripe_count: int = Field(default=0, description="未成熟数量")
    maturity_ratio: float = Field(default=0, description="成熟度百分比")
    detections: list[VlmDetection] = Field(default_factory=list, description="检测结果列表")
    annotated_image_base64: str = Field(default="", description="标注图片 base64")
    maturity_level: str = Field(default="", description="整体成熟度等级")
    maturity_detail: str = Field(default="", description="成熟度评估详细描述")
    planting_advice: str = Field(default="", description="种植建议")
    pest_disease: str = Field(default="", description="病虫害识别结果")
    overall_summary: str = Field(default="", description="综合分析总结")


_DETECTION_PROMPT = """你是番茄检测与成熟度分级助手。请检测图片中【所有】番茄(包括未成熟青番茄、被部分遮挡的番茄),不要遗漏。
对每个番茄输出一个检测结果,包含:
- "box": 番茄外接矩形的相对坐标 [x1, y1, x2, y2],取值 0-1000(左上角为原点,分别除以图片宽高后乘以 1000)
- "class_name": 成熟度,严格从以下六级中选择一个: 绿熟 / 转色 / 半熟 / 粉红 / 浅红 / 红熟
  分级依据(颜色占比): 绿熟:果实全绿,表面光亮; 转色:果顶出现 1-10% 变色; 半熟:变色 10-30%; 粉红:变色 30-60%,整体偏橙粉; 浅红:变色 60-90%; 红熟:90% 以上变红,完全成熟
- "confidence": 0-1 的浮点数,表示你对该番茄检测和分级把握的自评置信度

请严格按照以下 JSON 格式返回（不要包含其他文字）：
{
  "detections": [
    {"class_name": "红熟", "box": [x1, y1, x2, y2], "confidence": 0.95}
  ],
  "planting_advice": "种植建议",
  "pest_disease": "病虫害识别结果"
}

如果图中没有番茄，detections 返回空数组 []。"""


# 类别颜色映射 (RGB) - 六级分类
_CLASS_COLORS = {
    # 成熟（红）
    "红熟": (255, 0, 0),
    "浅红": (192, 57, 43),
    "成熟": (220, 50, 50),
    # 半成熟（橙/黄）
    "粉红": (231, 76, 60),
    "转色": (241, 196, 15),
    "半熟": (230, 126, 34),
    "半成熟": (220, 180, 50),
    # 未成熟（绿）
    "绿熟": (46, 204, 113),
    "未成熟": (50, 180, 50),
}


class VlmService:
    """大模型视觉识别服务（单例）"""

    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self._api_key: str = ""
        self._base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._model: str = "qwen3-vl-plus"

    def initialize(self) -> bool:
        """初始化客户端，返回是否可用"""
        self._api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not self._api_key:
            logger.warning("DASHSCOPE_API_KEY 未配置，大模型视觉识别不可用")
            return False

        self._base_url = os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self._model = os.getenv("VLM_MODEL", "qwen3-vl-plus")

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        logger.info(f"大模型视觉识别服务初始化成功 (model={self._model})")
        return True

    @property
    def is_ready(self) -> bool:
        return self._client is not None and bool(self._api_key)

    async def analyze_image(self, image_bytes: bytes) -> VlmAnalysisResult:
        """分析图片，返回带标框的结果

        Args:
            image_bytes: 图片的原始字节

        Returns:
            分析结果（含标注图片）
        """
        if not self.is_ready:
            return VlmAnalysisResult(
                overall_summary="大模型视觉识别服务未配置，请设置 DASHSCOPE_API_KEY"
            )

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _DETECTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        },
                    ],
                }
            ]

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=2048,
                temperature=0.2,
            )

            content = response.choices[0].message.content or ""
            result = self._parse_response(content, image_bytes)
            return result

        except Exception as e:
            logger.error(f"大模型视觉分析失败: {e}")
            return VlmAnalysisResult(
                overall_summary=f"分析失败：{str(e)}"
            )

    async def analyze_base64(self, image_base64: str) -> VlmAnalysisResult:
        """分析 base64 编码的图片

        Args:
            image_base64: base64 编码的图片（可带 data:image/... 前缀）
        """
        # 去除 data:image/... 前缀
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_base64)
        return await self.analyze_image(image_bytes)

    @staticmethod
    def _parse_response(content: str, image_bytes: bytes) -> VlmAnalysisResult:
        """解析模型返回的 JSON 文本，并绘制标框图"""
        # 尝试提取 JSON 块
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            return VlmAnalysisResult(overall_summary=content)

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return VlmAnalysisResult(overall_summary=content)

        detections_raw = data.get("detections", [])
        detections = []
        for det in detections_raw:
            box = det.get("box", [0, 0, 0, 0])
            if len(box) == 4:
                detections.append(VlmDetection(
                    class_name=det.get("class_name", "未知"),
                    confidence=det.get("confidence", 0.9),
                    box=box,
                ))

        # 统计（六级分类合并为三级）
        total = len(detections)
        ripe_keywords = ("红熟", "浅红", "成熟")
        half_keywords = ("粉红", "转色", "半熟", "半成熟")
        unripe_keywords = ("绿熟", "未成熟")
        ripe = sum(1 for d in detections if d.class_name in ripe_keywords)
        half = sum(1 for d in detections if d.class_name in half_keywords)
        unripe = sum(1 for d in detections if d.class_name in unripe_keywords)
        maturity_ratio = round((ripe / total * 100) if total > 0 else 0, 2)

        # 整体成熟度等级
        if total == 0:
            maturity_level = "未检测到"
        elif ripe / total > 0.5:
            maturity_level = "成熟"
        elif (ripe + half) / total > 0.5:
            maturity_level = "半成熟"
        else:
            maturity_level = "未成熟"

        # 绘制标框图
        annotated_base64 = ""
        if detections and image_bytes:
            try:
                annotated_base64 = VlmService._annotate_image(image_bytes, detections)
            except Exception as e:
                logger.error(f"绘制标框图失败: {e}")

        return VlmAnalysisResult(
            total_count=total,
            ripe_count=ripe,
            half_ripe_count=half,
            unripe_count=unripe,
            maturity_ratio=maturity_ratio,
            detections=detections,
            annotated_image_base64=annotated_base64,
            maturity_level=maturity_level,
            maturity_detail=data.get("maturity_detail", f"检测到 {total} 个番茄，成熟 {ripe}，半成熟 {half}，未成熟 {unripe}"),
            planting_advice=data.get("planting_advice", ""),
            pest_disease=data.get("pest_disease", ""),
            overall_summary=data.get("overall_summary", f"共检测 {total} 个番茄，成熟度 {maturity_ratio}%"),
        )

    @staticmethod
    def _annotate_image(image_bytes: bytes, detections: list[VlmDetection]) -> str:
        """在图片上绘制检测框，返回 base64

        坐标转换：模型返回相对坐标 0-1000，需要转换为像素坐标
        """
        # 加载图片
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_width, img_height = image.size
        draw = ImageDraw.Draw(image)

        # 加载字体
        font = VlmService._load_font(18)

        logger.info(f"标注图片尺寸: {img_width}x{img_height}")

        for det in detections:
            # 相对坐标 0-1000 → 像素坐标
            x1 = int(det.box[0] / 1000 * img_width)
            y1 = int(det.box[1] / 1000 * img_height)
            x2 = int(det.box[2] / 1000 * img_width)
            y2 = int(det.box[3] / 1000 * img_height)

            color = _CLASS_COLORS.get(det.class_name, (128, 128, 128))
            label = f"{det.class_name} {det.confidence:.1%}"

            logger.info(f"标框: {det.class_name} 原始={det.box} → 像素=[{x1},{y1},{x2},{y2}]")

            # 画边界框
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            # 文字背景
            bbox = draw.textbbox((x1, y1), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.rectangle(
                [x1, y1 - text_h - 6, x1 + text_w + 8, y1],
                fill=color,
            )

            # 文字
            draw.text((x1 + 4, y1 - text_h - 3), label, fill=(255, 255, 255), font=font)

        # 转为 base64
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """加载中文字体"""
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()


# 模块级单例
vlm_service = VlmService()
