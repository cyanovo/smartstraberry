"""摄像头管理 —— 封装 OpenCV VideoCapture"""

from __future__ import annotations

import os

import cv2
import numpy as np

from yuxi.utils import logger


class CameraManager:
    """本地摄像头管理器"""

    def __init__(self):
        self._default_camera_id = int(os.getenv("CAMERA_ID", "0"))
        self._width = int(os.getenv("CAMERA_WIDTH", "1280"))
        self._height = int(os.getenv("CAMERA_HEIGHT", "720"))
        self._enabled = os.getenv("CAMERA_ENABLED", "true").lower() in ("true", "1")

    @property
    def default_camera_id(self) -> int:
        return self._default_camera_id

    @property
    def enabled(self) -> bool:
        return self._enabled

    def list_cameras(self) -> list[dict]:
        """列出所有可用摄像头

        遍历 camera_id 0-9，检测哪些可用。
        Returns:
            [{"id": 0, "name": "摄像头 0 (内置)"}, ...]
        """
        cameras = []
        if not self._enabled:
            return cameras

        for cam_id in range(10):
            try:
                cap = cv2.VideoCapture(cam_id)
                if cap.isOpened():
                    # 尝试读取一帧确认真正可用
                    ret, _ = cap.read()
                    if ret:
                        # 获取摄像头名称
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                        if cam_id == 0:
                            name = f"内置摄像头 (ID: 0, {width}x{height})"
                        else:
                            name = f"USB 摄像头 (ID: {cam_id}, {width}x{height})"

                        cameras.append({
                            "id": cam_id,
                            "name": name,
                            "resolution": f"{width}x{height}",
                        })
                cap.release()
            except Exception:
                continue

        return cameras

    def is_available(self, camera_id: int | None = None) -> bool:
        """检查摄像头是否可用"""
        if not self._enabled:
            return False
        cam_id = camera_id if camera_id is not None else self._default_camera_id
        try:
            cap = cv2.VideoCapture(cam_id)
            available = cap.isOpened()
            if available:
                ret, _ = cap.read()
                available = ret
            cap.release()
            return available
        except Exception as e:
            logger.error(f"摄像头检测失败 (id={cam_id}): {e}")
            return False

    def capture(self, camera_id: int | None = None) -> np.ndarray | None:
        """捕获一帧图像

        Args:
            camera_id: 摄像头 ID，None 使用默认

        Returns:
            BGR 格式的 numpy 数组，失败返回 None
        """
        if not self._enabled:
            logger.warning("摄像头未启用")
            return None

        cam_id = camera_id if camera_id is not None else self._default_camera_id

        try:
            cap = cv2.VideoCapture(cam_id)

            if not cap.isOpened():
                logger.error(f"无法打开摄像头 (id={cam_id})")
                cap.release()
                return None

            # 设置分辨率
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)

            # 丢弃前几帧（摄像头预热）
            for _ in range(3):
                cap.read()

            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                logger.error(f"摄像头捕获失败 (id={cam_id})")
                return None

            logger.info(f"摄像头捕获成功: {frame.shape[1]}x{frame.shape[0]} (camera={cam_id})")
            return frame

        except Exception as e:
            logger.error(f"摄像头捕获异常 (id={cam_id}): {e}")
            return None

    def get_status(self, camera_id: int | None = None) -> dict:
        """获取摄像头状态"""
        cam_id = camera_id if camera_id is not None else self._default_camera_id
        return {
            "camera_id": cam_id,
            "enabled": self._enabled,
            "available": self.is_available(cam_id) if self._enabled else False,
            "resolution": f"{self._width}x{self._height}",
        }


# 模块级单例
camera_manager = CameraManager()
