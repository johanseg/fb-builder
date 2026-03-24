import pytest

def test_assemble_modules(client, auth_headers):
    # Setup Brand and Product
    brand_response = client.post(
        "/api/v1/brands/",
        json={"name": "Test Brand Assembly", "industry": "Tech", "company_description": "A tech brand", "colors": {"primary": "#000000", "secondary": "#111111", "highlight": "#222222"}, "tone_of_voice": "Professional"},
        headers=auth_headers
    )
    brand_id = brand_response.json()["id"]

    product_response = client.post(
        "/api/v1/products/",
        json={"brand_id": brand_id, "name": "Assembly Product", "description": "Desc", "price": 19.99},
        headers=auth_headers
    )
    product_id = product_response.json()["id"]

    # Create 4 modules
    intro = client.post("/api/v1/ad-modules/", json={"product_id": product_id, "module_type": "intro", "content": "Intro text", "generation_metadata": {"hook_type": "Pain", "format": "Question"}, "performance_score": 0, "tags": []}, headers=auth_headers).json()
    bridge = client.post("/api/v1/ad-modules/", json={"product_id": product_id, "module_type": "bridge", "content": "Bridge text", "generation_metadata": {"bridge_type": "Mechanism"}, "performance_score": 0, "tags": []}, headers=auth_headers).json()
    core = client.post("/api/v1/ad-modules/", json={"product_id": product_id, "module_type": "core", "content": "Core text", "generation_metadata": {"core_type": "Logic Lock"}, "performance_score": 0, "tags": []}, headers=auth_headers).json()
    cta = client.post("/api/v1/ad-modules/", json={"product_id": product_id, "module_type": "cta", "content": "CTA text", "generation_metadata": {"cta_type": "Urgency"}, "performance_score": 0, "tags": []}, headers=auth_headers).json()

    # Assemble
    response = client.post(
        "/api/v1/naming/assemble",
        json={
            "intro_id": intro["id"],
            "bridge_id": bridge["id"],
            "core_id": core["id"],
            "cta_id": cta["id"]
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "I-PAIN-Q" in data["bundle_code"]
    assert "B-MEC" in data["bundle_code"]
    assert "C-LOGIC" in data["bundle_code"]
    assert "CTA-URGENCY" in data["bundle_code"]
    assert "Intro text" in data["assembled_text"]
    assert "Bridge text" in data["assembled_text"]
    assert "Core text" in data["assembled_text"]
    assert "CTA text" in data["assembled_text"]
