"""Managed upload storage shared by API writers."""

from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path

import boto3

from app.core.config import settings

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def store_upload(source, filename: str) -> str:
    """Store a seekable upload stream and return its public reference."""
    source.seek(0)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if settings.r2_enabled:
        _r2_client().upload_fileobj(
            source,
            settings.R2_BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": content_type},
        )
        return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{filename}"

    UPLOAD_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
    with (UPLOAD_DIR / filename).open("wb") as destination:
        shutil.copyfileobj(source, destination)
    return f"/uploads/{filename}"
