"""Auth service regression tests."""

from unittest.mock import MagicMock


def test_purge_expired_refresh_tokens_deletes_only_expired(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.services.auth_service import purge_expired_refresh_tokens

    db_session = MagicMock()
    query = db_session.query.return_value
    filtered_query = query.filter.return_value
    filtered_query.delete.return_value = 3

    deleted_count = purge_expired_refresh_tokens(db_session)

    assert deleted_count == 3
    db_session.query.assert_called_once()
    query.filter.assert_called_once()
    filtered_query.delete.assert_called_once_with(synchronize_session=False)
    db_session.commit.assert_called_once()
