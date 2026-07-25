from app.models import Brand, User
from app.services.meta_reporting_service import MetaReportingService


def test_reporting_read_requires_auth(client):
    response = client.get("/api/v1/performance/meta/report?brand_id=missing")

    assert response.status_code == 401


def test_reporting_read_uses_dedicated_permission(client, auth_headers, monkeypatch):
    requested = []

    def allow_reporting_read(self, permission):
        requested.append(permission)
        return permission == "reporting:read"

    monkeypatch.setattr(User, "has_permission", allow_reporting_read)
    response = client.get("/api/v1/performance/meta/report?brand_id=missing", headers=auth_headers)

    assert response.status_code == 404
    assert requested == ["reporting:read"]


def test_reporting_policy_uses_dedicated_write_permission(client, auth_headers, db_session, monkeypatch):
    requested = []
    monkeypatch.setattr(User, "has_permission", lambda self, permission: requested.append(permission) is None and permission == "reporting:write")
    brand = Brand(name="Reporting policy endpoint")
    db_session.add(brand)
    db_session.commit()

    response = client.put(f"/api/v1/performance/meta/brands/{brand.id}/policy", json={"min_spend": 10}, headers=auth_headers)

    assert response.status_code == 200
    assert requested == ["reporting:write"]


def test_admin_mapping_requires_allowlist_and_live_meta_access(client, auth_headers, db_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "act_123")
    monkeypatch.setattr(MetaReportingService, "accessible_account", lambda self, account_id: {"id": account_id, "currency": "USD"})
    brand = Brand(name="Mapping endpoint")
    db_session.add(brand)
    db_session.commit()

    response = client.post(
        f"/api/v1/performance/meta/accounts?brand_id={brand.id}&meta_account_id=123&currency=USD&timezone=UTC",
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["meta_account_id"] == "act_123"


def test_admin_can_start_read_only_brand_sync(client, auth_headers, db_session, monkeypatch):
    brand = Brand(name="Manual sync endpoint")
    db_session.add(brand)
    db_session.commit()
    monkeypatch.setattr(MetaReportingService, "sync_brand", lambda self, brand_id: [])
    requested = []
    monkeypatch.setattr(User, "has_permission", lambda self, permission: requested.append(permission) is None and permission == "reporting:sync")

    response = client.post(f"/api/v1/performance/meta/sync?brand_id={brand.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []
    assert requested == ["reporting:sync"]
