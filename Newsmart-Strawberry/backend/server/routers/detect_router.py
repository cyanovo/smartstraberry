"""番茄成熟度检测 API"""

from __future__ import annotations

import base64

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field

from server.utils.auth_middleware import get_required_user
from yuxi.services.detect_service import detect_service
from yuxi.utils import logger

detect = APIRouter(prefix="/detect", tags=["番茄成熟度检测"])


class CameraDetectRequest(BaseModel):
    """摄像头检测请求"""

    zone: str = Field(default="A", description="棚区标识 (A/B/C)")
    camera_id: int | None = Field(default=None, description="摄像头 ID，None 使用默认")
    conf_threshold: float | None = Field(default=None, description="置信度阈值")


@detect.post("/camera")
async def camera_detect(req: CameraDetectRequest, _=Depends(get_required_user)):
    """拍照并执行成熟度检测"""
    if not detect_service.is_ready:
        raise HTTPException(status_code=503, detail="检测模型未就绪，请检查模型文件")

    try:
        result = await detect_service.capture_and_detect(
            zone=req.zone,
            camera_id=req.camera_id,
            conf_threshold=req.conf_threshold,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"摄像头检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@detect.post("/image")
async def image_detect(
    file: UploadFile,
    zone: str = "A",
    conf_threshold: float | None = None,
    _=Depends(get_required_user),
):
    """上传图片进行成熟度检测"""
    if not detect_service.is_ready:
        raise HTTPException(status_code=503, detail="检测模型未就绪")

    try:
        # 读取上传文件
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="无法解码图片")

        result = await detect_service.detect_from_image(
            image=image,
            zone=zone,
            conf_threshold=conf_threshold,
        )
        return result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@detect.get("/history")
async def get_history(
    zone: str | None = None,
    limit: int = 20,
    _=Depends(get_required_user),
):
    """查询检测历史记录"""
    try:
        records = await detect_service.get_history(zone=zone, limit=limit)
        return [r.model_dump() for r in records]
    except Exception as e:
        logger.error(f"查询检测历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@detect.get("/stats")
async def get_stats(_=Depends(get_required_user)):
    """获取各区域成熟度统计"""
    try:
        return await detect_service.get_stats()
    except Exception as e:
        logger.error(f"获取检测统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@detect.get("/camera/status")
async def get_camera_status(_=Depends(get_required_user)):
    """获取摄像头状态"""
    return await detect_service.get_camera_status()


@detect.get("/camera/list")
async def list_cameras(_=Depends(get_required_user)):
    """列出所有可用摄像头"""
    from yuxi.detect.camera import camera_manager
    return camera_manager.list_cameras()
