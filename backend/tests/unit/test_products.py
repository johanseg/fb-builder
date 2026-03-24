import pytest
from fastapi.testclient import TestClient

def test_create_and_read_product_brief(client: TestClient, auth_headers: dict):
    # Create brand
    brand_data = {
        "name": "Test Brand",
        "colors": {"primary": "#fff", "secondary": "#000", "highlight": "#f00"}
    }
    resp = client.post("/api/v1/brands/", json=brand_data, headers=auth_headers)
    assert resp.status_code == 200, resp.json()
    brand_id = resp.json()["id"]

    # Create product with brief fields
    product_data = {
        "name": "Widget X",
        "description": "A very useful widget",
        "brand_id": brand_id,
        "pain_points": ["Too much time wasted", "Manual errors"],
        "desired_outcomes": ["Automated process", "Zero errors"],
        "root_causes": ["Legacy software"],
        "proof_points": ["Used by 10k businesses"],
        "differentiators": ["Proprietary AI algorithm"],
        "risk_reversals": ["30-day money back guarantee"]
    }
    resp = client.post("/api/v1/products/", json=product_data, headers=auth_headers)
    assert resp.status_code == 200, resp.json()
    product = resp.json()
    assert product["name"] == "Widget X"
    assert product["pain_points"] == ["Too much time wasted", "Manual errors"]
    assert product["risk_reversals"] == ["30-day money back guarantee"]
    product_id = product["id"]

    # Read product
    resp = client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["proof_points"] == ["Used by 10k businesses"]

    # Update product brief fields
    update_data = {
        "name": "Widget X Pro",
        "pain_points": ["Even more time wasted"]
    }
    resp = client.put(f"/api/v1/products/{product_id}", json=update_data, headers=auth_headers)
    assert resp.status_code == 200
    updated_product = resp.json()
    assert updated_product["name"] == "Widget X Pro"
    assert updated_product["pain_points"] == ["Even more time wasted"]
    assert updated_product["desired_outcomes"] == ["Automated process", "Zero errors"]
