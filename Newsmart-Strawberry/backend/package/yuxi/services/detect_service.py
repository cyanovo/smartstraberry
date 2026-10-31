"""番茄成熟度检测服务"""

from __future__ import annotations

import uuid
from datetime import datetime

import cv2
import numpy as np

from yuxi.detect.camera import camera_manager
from yuxi.detect.core import detector
from yuxi.detect.schemas import DetectResult
from yuxi.repositories.detect_repository import detect_repository
from yuxi.utils import logger


class DetectService:
    """检测业务服务（单例）"""

    def __init__(self):
        self._model_loaded = False

    async def initialize(self):
        """初始化检测模型（由 lifespan 调用）"""
        self._model_loaded = detector.load_model()
        if self._model_loaded:
            logger.info("检测服务初始化成功")
        else:
            logger.warning("检测模型未加载，检测功能不可用")

    @property
    def is_ready(self) -> bool:
        return self._model_loaded and detector.is_ready

    async def capture_and_detect(
        self,
        zone: str = "A",
        camera_id: int | None = None,
        conf_threshold: float | None = None,
    ) -> DetectResult:
        """拍照并执行成熟度检测

        Args:
            zone: 棚区标识 (A/B/C)
            camera_id: 摄像头 ID，None 使用默认
            conf_threshold: 置信度阈值，None 使用默认

        Returns:
            检测结果
        """
        # 捕获图像
        if camera_id is not None:
            from yuxi.detect.camera import CameraManager
            import os
            old_id = os.environ.get("CAMERA_ID")
            os.environ["CAMERA_ID"] = str(camera_id)
            cam = CameraManager()
            if old_id is not None:
                os.environ["CAMERA_ID"] = old_id
            elif "CAMERA_ID" in os.environ:
                del os.environ["CAMERA_ID"]
            image = cam.capture()
        else:
            image = camera_manager.capture()

        if image is None:
            return self._empty_result(zone, "摄像头捕获失败")

        return await self.detect_from_image(image, zone, conf_threshold)

    async def detect_from_image(
        self,
        image: np.ndarray,
        zone: str = "A",
        conf_threshold: float | None = None,
    ) -> DetectResult:
        """从图像执行检测

        Args:
            image: BGR 格式的 numpy 数组
            zone: 棚区标识
            conf_threshold: 置信度阈值

        Returns:
            检测结果
        """
        if not self.is_ready:
            return self._empty_result(zone, "检测模型未就绪")

        # 执行检测
        detections = detector.detect(image, conf_threshold)

        # 统计 (class_id: 0=Unripe, 1=Half-ripe, 2=Ripe)
        total = len(detections)
        unripe = sum(1 for d in detections if d.class_id == 0)
        half = sum(1 for d in detections if d.class_id == 1)
        ripe = sum(1 for d in detections if d.class_id == 2)
        maturity_ratio = round((ripe / total * 100) if total > 0 else 0, 2)

        # 生成标注图片
        annotated = detector.annotate_image(image, detections)
        _, buffer = cv2.imencode(".jpg", annotated)
        import base64
        annotated_base64 = base64.b64encode(buffer).decode("utf-8")

        # 生成建议
        recommendation = detector.generate_recommendation(total, ripe, half, unripe)

        # 构建结果
        result = DetectResult(
            id=uuid.uuid4().hex[:16],
            zone=zone,
            camera_id=camera_manager.camera_id,
            total_count=total,
            ripe_count=ripe,
            half_ripe_count=half,
            unripe_count=unripe,
            maturity_ratio=maturity_ratio,
            confidence_threshold=conf_threshold or detector.confidence_threshold,
            detections=detections,
            recommendation=recommendation,
            annotated_image_base64=annotated_base64,
            created_at=datetime.now(),
        )

        # 持久化（不保存 base64 图片，节省存储）
        try:
            await detect_repository.save_record(result)
        except Exception as e:
            logger.error(f"检测记录保存失败: {e}")

        return result

    async def get_history(
        self, zone: str | None = None, limit: int = 20
    ) -> list[DetectResult]:
        """查询检测历史"""
        return await detect_repository.get_records(zone=zone, limit=limit)

    async def get_stats(self) -> dict:
        """获取各区域成熟度统计"""
        return await detect_repository.get_stats()

    async def get_camera_status(self) -> dict:
        """获取摄像头状态"""
        return {
            **camera_manager.get_status(),
            "model_ready": self.is_ready,
        }

    @staticmethod
    def _empty_result(zone: str, message: str) -> DetectResult:
        """生成空结果"""
        return DetectResult(
            id=uuid.uuid4().hex[:16],
            zone=zone,
            camera_id=camera_manager.camera_id,
            total_count=0,
            ripe_count=0,
            half_ripe_count=0,
            unripe_count=0,
            maturity_ratio=0,
            recommendation=message,
            created_at=datetime.now(),
        )


# 模块级单例
detect_service = DetectService()
