from unittest.mock import MagicMock

import pytest

from app.services.facebook_service import FacebookService


def test_empty_allowlist_fails_closed(monkeypatch):
    monkeypatch.delenv("ALLOWED_FB_ACCOUNTS", raising=False)
    service = object.__new__(FacebookService)
    service.api = MagicMock()
    service.account = None

    assert service.get_ad_accounts() == []
    with pytest.raises(PermissionError):
        service._get_account("act_123")


def test_allowlist_normalizes_account_ids(monkeypatch):
    monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "123")
    service = object.__new__(FacebookService)
    service.api = MagicMock()
    service.account = None

    assert FacebookService._allowed_account_ids() == {"act_123"}
