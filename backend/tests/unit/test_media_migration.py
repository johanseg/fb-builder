from io import BytesIO

from scripts.migrate_local_uploads_to_r2 import fingerprint, local_name, local_references, replace_reference


def test_local_name_accepts_only_flat_managed_uploads():
    assert local_name("/uploads/example.mp4") == "example.mp4"
    assert local_name("uploads/example.mp4") is None
    assert local_name("/uploads/../secret") is None
    assert local_name("/uploads/nested/example.mp4") is None


def test_fingerprint_reports_exact_size_and_sha256():
    result = fingerprint(BytesIO(b"media"))

    assert result == {"size": 5, "sha256": "721c9525ade2ea8903d343ef25cf68b9bf4ab0aad56bb7b01fbe48d09bc7fcf4"}


def test_json_reference_inventory_rewrites_only_managed_uploads():
    source = {"media": ["/uploads/persona.png", "https://example.com/external.png"]}

    assert local_references(source) == {"/uploads/persona.png"}
    assert replace_reference(source, "/uploads/persona.png", "https://r2.example/persona.png") == {
        "media": ["https://r2.example/persona.png", "https://example.com/external.png"],
    }
