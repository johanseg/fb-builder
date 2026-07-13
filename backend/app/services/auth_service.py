"""Authentication-related service helpers."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import RefreshToken


def purge_expired_refresh_tokens(db: Session) -> int:
    """Delete expired refresh tokens and return the number of removed rows."""
    deleted_count = db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.now(timezone.utc)
    ).delete(synchronize_session=False)
    db.commit()
    return deleted_count
