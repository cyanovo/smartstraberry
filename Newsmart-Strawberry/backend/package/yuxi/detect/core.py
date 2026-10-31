"""番茄成熟度检测核心 —— 基于 YOLO 模型"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from yuxi.detect.schemas import CLASS_COLORS, MATURITY_CLASSES, Detection
from yuxi.utils import logger

# 模型目录
_MODEL_DIR = Path(__file__).parent / "models"

# 尝试加载依赖
try:
    from ultralytics import YOLO

    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning("ultralytics 未安装，检测功能不可用")

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class StrawberryDetector:
    """番茄成熟度检测器（单例）"""

    def __init__(self):
        self.device = "cuda" if HAS_TORCH and torch.cuda.is_available() else "cpu"
        self.model: YOLO | None = None
        self.model_path = os.getenv("DETECT_MODEL_PATH", str(_MODEL_DIR / "best.pt"))
        self.confidence_threshold = float(os.getenv("DETECT_CONFIDENCE_THRESHOLD", "0.5"))
        self._loaded = False

    def load_model(self) -> bool:
        """加载 YOLO 模型，返回是否成功"""
        if self._loaded:
            return True

        if not HAS_YOLO:
            logger.error("ultralytics 未安装，无法加载检测模型")
            return False

        try:
            if not os.path.exists(self.model_path):
                logger.error(f"模型文件不存在: {self.model_path}")
                return False

            logger.info(f"加载检测模型: {self.model_path} (device={self.device})")
            self.model = YOLO(self.model_path)
            self._loaded = True

            if hasattr(self.model, "names"):
                logger.info(f"模型类别映射: {self.model.names}")

            logger.info("检测模型加载成功")
            return True

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self._loaded = False
            return False

    @property
    def is_ready(self) -> bool:
        """模型是否就绪"""
        return self._loaded and self.model is not None

    def detect(self, image: np.ndarray, conf_threshold: float | None = None) -> list[Detection]:
        """执行检测

        Args:
            image: BGR 格式的 numpy 数组
            conf_threshold: 置信度阈值，None 使用默认值

        Returns:
            检测结果列表
        """
        if not self.is_ready:
            logger.warning("模型未就绪，无法执行检测")
            return []

        conf = conf_threshold or self.confidence_threshold

        try:
            results = self.model(image, conf=conf, verbose=False)
            detections = []

            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())

                    detections.append(
                        Detection(
                            class_id=class_id,
                            class_name=MATURITY_CLASSES.get(class_id, "未知"),
                            confidence=round(confidence, 4),
                            box=[int(x1), int(y1), int(x2), int(y2)],
                        )
                    )

            return detections

        except Exception as e:
            logger.error(f"检测执行失败: {e}")
            return []

    def annotate_image(self, image: np.ndarray, detections: list[Detection]) -> np.ndarray:
        """在图像上标注检测结果

        Args:
            image: BGR 格式的原始图像
            detections: 检测结果列表

        Returns:
            标注后的 BGR 图像
        """
        # 转为 PIL 图像（支持中文标注）
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        draw = ImageDraw.Draw(pil_image)

        # 加载中文字体
        font = self._load_font(20)

        for det in detections:
            x1, y1, x2, y2 = det.box
            color = CLASS_COLORS.get(det.class_id, (255, 255, 255))
            text = f"{det.class_name} {det.confidence:.2f}"

            # 画边界框
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

            # 文字背景
            bbox = draw.textbbox((x1, y1), text, font=font)
            draw.rectangle([bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2], fill=color)

            # 文字
            draw.text((x1, y1 - 5), text, fill=(255, 255, 255), font=font)

        # 转回 OpenCV 格式
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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

    @staticmethod
    def generate_recommendation(
        total: int, ripe: int, half: int, unripe: int
    ) -> str:
        """生成采摘建议"""
        if total == 0:
            return "未检测到番茄，请检查摄像头画面"

        ripe_ratio = ripe / total

        if ripe_ratio > 0.7:
            return "大量番茄已成熟，建议立即采摘！"
        elif ripe_ratio > 0.4:
            return "部分番茄已成熟，建议分批采摘"
        elif ripe_ratio > 0.2:
            return "番茄正在成熟中，预计 3-5 天可采摘"
        else:
            return "番茄尚在生长期，请继续培育"


# 模块级单例
detector = StrawberryDetector()
