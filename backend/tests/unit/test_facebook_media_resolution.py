import pytest

from app.services import facebook_service
from app.services.facebook_service import FacebookService, IMAGE_MAX_BYTES, VIDEO_MAX_BYTES


def _service():
    return object.__new__(FacebookService)


def test_remote_media_uses_shared_guard_with_configured_hosts(monkeypatch, tmp_path):
    monkeypatch.setenv("R2_PUBLIC_URL", "https://assets.example.r2.dev")
    monkeypatch.setenv("ALLOWED_MEDIA_DOMAINS", "media.customer.example")
    expected = tmp_path / "image.jpg"
    expected.write_bytes(b"image")
    captured = {}

    def guarded(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return str(expected)

    monkeypatch.setattr(facebook_service, "download_remote_media_to_tempfile", guarded)
    path, cleanup = _service()._resolve_media_source(
        "https://media.customer.example/ad.jpg", media_kind="image", default_suffix=".jpg", timeout=30,
        allowed_extensions={".jpg"},
    )

    assert (path, cleanup) == (str(expected), True)
    assert captured["max_bytes"] == IMAGE_MAX_BYTES
    assert set(captured["allowed_domains"]) == {"assets.example.r2.dev", "fal.media", "v3.fal.media", "cdn.fal.ai", "storage.googleapis.com", "media.customer.example"}


@pytest.mark.parametrize("reason", ["redirect target is private", "Remote media exceeds allowed size"])
def test_guard_rejections_leave_no_caller_tempfile(monkeypatch, reason, tmp_path):
    monkeypatch.setattr(
        facebook_service,
        "download_remote_media_to_tempfile",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError(reason)),
    )
    with pytest.raises(ValueError, match=reason):
        _service()._resolve_media_source(
            "https://fal.media/creative.mp4", media_kind="video", default_suffix=".mp4", timeout=120,
            allowed_extensions={".mp4"},
        )
    assert list(tmp_path.iterdir()) == []


def test_private_media_url_is_rejected_before_fetch():
    with pytest.raises(ValueError):
        _service()._resolve_media_source(
            "https://127.0.0.1/image.jpg", media_kind="image", default_suffix=".jpg", timeout=30,
            allowed_extensions={".jpg"},
        )
    assert VIDEO_MAX_BYTES == 500 * 1024 * 1024
