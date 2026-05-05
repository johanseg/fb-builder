from app.api.v1.generated_ads import (
    build_prompt_variation,
    get_persistable_template_id,
    is_configured_fal_api_key,
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
