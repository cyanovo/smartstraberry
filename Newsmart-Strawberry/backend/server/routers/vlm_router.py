"""大模型视觉识别 API 路由"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from server.utils.auth_middleware import get_required_user
from yuxi.services.vlm_service import vlm_service
from yuxi.utils import logger

vlm = APIRouter(prefix="/vlm", tags=["大模型视觉识别"])


class Base64Request(BaseModel):
    """base64 图片请求"""

    image_base64: str = Field(..., description="base64 编码的图片")


@vlm.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    _=Depends(get_required_user),
):
    """上传图片进行大模型视觉分析"""
    if not vlm_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="大模型视觉识别服务未配置，请在环境变量中设置 DASHSCOPE_API_KEY",
        )

    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        result = await vlm_service.analyze_image(content)
        return {"ok": True, "result": result.model_dump()}
    except Exception as e:
        logger.error(f"大模型分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@vlm.post("/analyze-base64")
async def analyze_base64(
    req: Base64Request,
    _=Depends(get_required_user),
):
    """接收 base64 图片进行大模型视觉分析"""
    if not vlm_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="大模型视觉识别服务未配置，请在环境变量中设置 DASHSCOPE_API_KEY",
        )

    if not req.image_base64:
        raise HTTPException(status_code=400, detail="图片数据为空")

    try:
        result = await vlm_service.analyze_base64(req.image_base64)
        return {"ok": True, "result": result.model_dump()}
    except Exception as e:
        logger.error(f"大模型分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
