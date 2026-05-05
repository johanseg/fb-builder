from app.api.v1.generated_ads import (
    build_prompt_variation,
    get_persistable_template_id,
    is_configured_fal_api_key,
    to_public_asset_url,
)


class FakeQuery:
    def __init__(self, exists):
        self.exists = exists

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return object() if self.exists else None


class FakeSession:
    def __init__(self, exists):
        self.exists = exists

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.exists)


def test_placeholder_fal_key_is_not_configured():
    assert not is_configured_fal_api_key("")
    assert not is_configured_fal_api_key("your-fal-ai-api-key")
    assert not is_configured_fal_api_key("your-real-key-here")
    assert is_configured_fal_api_key("fal-key:real-secret-token")


def test_style_archetype_template_id_is_not_persisted():
    assert get_persistable_template_id(FakeSession(False), "old-way-new-way") is None
    assert get_persistable_template_id(FakeSession(True), "winning-ad-id") == "winning-ad-id"
    assert get_persistable_template_id(FakeSession(False), None) is None


def test_prompt_variation_adds_distinct_generation_direction():
    base_prompt = "Base template prompt"

    first = build_prompt_variation(base_prompt, 0, 3, "Square")
    second = build_prompt_variation(base_prompt, 1, 3, "Square")

    assert base_prompt in first
    assert "Variation 1 of 3" in first
    assert "Variation 2 of 3" in second
    assert first != second


def test_upload_paths_are_returned_with_public_backend_origin(monkeypatch):
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://fb-builder-production.up.railway.app")

    url = to_public_asset_url("/uploads/generated_123.png")

    assert url == "https://fb-builder-production.up.railway.app/uploads/generated_123.png"


def test_upload_paths_prefer_request_origin():
    url = to_public_asset_url(
        "/uploads/generated_123.png",
        "https://fb-builder-production.up.railway.app/",
    )

    assert url == "https://fb-builder-production.up.railway.app/uploads/generated_123.png"


def test_configured_public_origin_overrides_internal_request_origin(monkeypatch):
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://fb-builder-production.up.railway.app")

    url = to_public_asset_url(
        "/uploads/generated_123.png",
        "http://internal-service.railway.internal/",
    )

    assert url == "https://fb-builder-production.up.railway.app/uploads/generated_123.png"


def test_railway_http_request_origin_is_upgraded_to_https():
    url = to_public_asset_url(
        "/uploads/generated_123.png",
        "http://fb-builder-production.up.railway.app/",
    )

    assert url == "https://fb-builder-production.up.railway.app/uploads/generated_123.png"


def test_schemeless_public_origin_is_normalized_to_https(monkeypatch):
    monkeypatch.setenv("RAILWAY_SERVICE_FB_BUILDER_URL", "fb-builder-production.up.railway.app")

    url = to_public_asset_url("/uploads/generated_123.png")

    assert url == "https://fb-builder-production.up.railway.app/uploads/generated_123.png"


def test_absolute_asset_urls_are_not_rewritten(monkeypatch):
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://fb-builder-production.up.railway.app")

    url = to_public_asset_url("https://fal.media/generated.png")

    assert url == "https://fal.media/generated.png"
