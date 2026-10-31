from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.background import BackgroundTask

from server.utils.auth_middleware import get_required_user
from yuxi.repositories.album_repository import album_repository
from yuxi.services import album_service

albums = APIRouter(prefix="/albums", tags=["草莓照片集"])


class CreateAlbum(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    cluster_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    plot: str = Field(default="", max_length=128)
    device_id: str = Field(default="", max_length=128)


@albums.get("")
async def list_albums(
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user=Depends(get_required_user)
):
    return await album_repository.list(user.department_id, limit, offset)


@albums.post("", status_code=201)
async def create_album(body: CreateAlbum, user=Depends(get_required_user)):
    return await album_service.create_album(body.model_dump(), user)


@albums.get("/photos/{photo_id}/file")
async def get_photo_file(photo_id: str, thumbnail: bool = False, user=Depends(get_required_user)):
    path, photo = await album_service.photo_file(photo_id, user, thumbnail)
    media = (
        "image/jpeg"
        if thumbnail
        else {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[photo["extension"]]
    )
    return FileResponse(
        path,
        media_type=media,
        filename=photo["filename"] if not thumbnail else None,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@albums.get("/{album_id}")
async def get_album(album_id: str, user=Depends(get_required_user)):
    return await album_service.require_album(album_id, user)


@albums.get("/{album_id}/photos")
async def list_photos(
    album_id: str, limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0), user=Depends(get_required_user)
):
    await album_service.require_album(album_id, user)
    return await album_repository.photos(album_id, user.department_id, limit, offset)


@albums.get("/{album_id}/archive")
async def download_album(album_id: str, user=Depends(get_required_user)):
    path = await album_service.album_archive(album_id, user)
    return FileResponse(
        path,
        media_type="application/zip",
        filename="album-originals.zip",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


@albums.post("/{album_id}/photos", status_code=201)
async def upload_photo(
    album_id: str,
    file: Annotated[UploadFile, File()],
    captured_at: Annotated[datetime | None, Form()] = None,
    user=Depends(get_required_user),
):
    return await album_service.upload_photo(album_id, file, captured_at, user)
