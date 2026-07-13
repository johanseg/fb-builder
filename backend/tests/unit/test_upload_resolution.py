"""Upload path resolution regression tests."""


def test_resolve_managed_upload_path_accepts_public_upload_url(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.core.utils import resolve_managed_upload_path

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    asset_path = upload_dir / "asset.png"
    asset_path.write_bytes(b"png")

    resolved = resolve_managed_upload_path("/uploads/asset.png", upload_dir)

    assert resolved == asset_path.resolve()


def test_resolve_managed_upload_path_accepts_legacy_relative_upload_path(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.core.utils import resolve_managed_upload_path

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    asset_path = upload_dir / "asset.mp4"
    asset_path.write_bytes(b"mp4")

    resolved = resolve_managed_upload_path("uploads/asset.mp4", upload_dir)

    assert resolved == asset_path.resolve()


def test_resolve_managed_upload_path_rejects_arbitrary_local_files(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")
    from app.core.utils import resolve_managed_upload_path

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    assert resolve_managed_upload_path("/etc/passwd", upload_dir) is None
    assert resolve_managed_upload_path("../uploads/asset.png", upload_dir) is None
    assert resolve_managed_upload_path("/uploads/../secret.txt", upload_dir) is None
