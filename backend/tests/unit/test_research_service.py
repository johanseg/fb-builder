"""Research service regression tests."""

from types import SimpleNamespace


def test_compute_content_hash_uses_external_id_when_available(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.services.research_service import ResearchService

    shared_copy = {
        "brand_name": "Acme",
        "headline": "Same headline",
        "ad_copy": "Same body",
        "cta_text": "Learn More",
        "media_type": "image",
        "ad_link": "https://example.com/ad",
    }

    first_ad = SimpleNamespace(external_id="library-1", **shared_copy)
    second_ad = SimpleNamespace(external_id="library-2", **shared_copy)

    assert ResearchService.compute_content_hash(first_ad) != ResearchService.compute_content_hash(second_ad)


def test_compute_content_hash_falls_back_to_media_identity_without_external_id(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.services.research_service import ResearchService

    first_ad = SimpleNamespace(
        external_id=None,
        brand_name="Acme",
        headline="Same headline",
        ad_copy="Same body",
        cta_text="Learn More",
        media_type="image",
        ad_link="https://example.com/ad-1",
    )
    second_ad = SimpleNamespace(
        external_id=None,
        brand_name="Acme",
        headline="Same headline",
        ad_copy="Same body",
        cta_text="Learn More",
        media_type="video",
        ad_link="https://example.com/ad-2",
    )

    assert ResearchService.compute_content_hash(first_ad) != ResearchService.compute_content_hash(second_ad)
