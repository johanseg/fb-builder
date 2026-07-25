import logging
import os
import uuid
from typing import Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.api_errors import log_and_raise_http_error
from app.core.deps import require_permission
from app.models import User
from app.services.storage import store_upload

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 500 * 1024 * 1024


def valid_media_signature(extension: str, header: bytes) -> bool:
    """Accept only the image/video container claimed by the filename."""
    signatures = {
        ".jpg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        ".gif": lambda value: value.startswith((b"GIF87a", b"GIF89a")),
        ".webp": lambda value: value.startswith(b"RIFF") and value[8:12] == b"WEBP",
        ".avi": lambda value: value.startswith(b"RIFF") and value[8:12] == b"AVI ",
        ".webm": lambda value: value.startswith(b"\x1aE\xdf\xa3"),
        ".mp4": lambda value: len(value) >= 8 and value[4:8] == b"ftyp",
        ".mov": lambda value: len(value) >= 8 and value[4:8] == b"ftyp",
    }
    return signatures[extension](header)


@router.post("/", response_model=Dict[str, str])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("ads:write")),
):
    try:
        safe_filename = os.path.basename(file.filename or "")
        file_extension = os.path.splitext(safe_filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type")

        is_video = file_extension in ALLOWED_VIDEO_EXTENSIONS
        max_size = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
        stream = file.file
        stream.seek(0, os.SEEK_END)
        if stream.tell() > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size / (1024 * 1024)}MB",
            )
        stream.seek(0)
        if not valid_media_signature(file_extension, stream.read(32)):
            raise HTTPException(status_code=400, detail="File content does not match its extension")

        filename = f"{uuid.uuid4()}{file_extension}"
        url = store_upload(stream, filename)
        return {"url": url, "media_type": "video" if is_video else "image"}
    except HTTPException:
        raise
    except Exception as exc:
        log_and_raise_http_error(logger, "File upload failed", exc)
