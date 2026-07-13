"""Shared helpers for logging and raising API errors consistently."""

from fastapi import HTTPException


def log_and_raise_http_error(
    logger,
    context: str,
    exc: Exception,
    *,
    status_code: int = 500,
    detail: str = "Internal server error",
    expose_detail: bool = False,
) -> None:
    """Log the full traceback and raise an HTTPException."""
    logger.exception(context)
    raise HTTPException(
        status_code=status_code,
        detail=str(exc) if expose_detail else detail,
    ) from exc
