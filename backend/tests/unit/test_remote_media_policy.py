"""SSRF and permitted-host policy checks for remote media."""

from app.core import utils


def test_media_policy_combines_known_r2_and_configured_hosts(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_URL", "https://media.example.test")
    monkeypatch.setenv("ALLOWED_MEDIA_DOMAINS", "assets.example.test")

    domains = utils.allowed_media_domains()

    assert "media.example.test" in domains
    assert "assets.example.test" in domains
    assert not utils.validate_url("https://public.example.test/image.png", domains)


def test_url_validation_rejects_private_dns_answers(monkeypatch):
    monkeypatch.setattr(
        utils.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("10.0.0.1", 443))],
    )

    assert not utils.validate_url("https://assets.example.test/image.png")
