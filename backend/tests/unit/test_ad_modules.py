import pytest

def test_create_ad_module(client, auth_headers):
    # Setup Brand and Product
    brand_response = client.post(
        "/api/v1/brands/",
        json={"name": "Test Brand Modules", "industry": "Tech", "company_description": "A tech brand", "colors": {"primary": "#000000", "secondary": "#111111", "highlight": "#222222"}, "tone_of_voice": "Professional"},
        headers=auth_headers
    )
    assert brand_response.status_code == 200
    brand_id = brand_response.json()["id"]

    product_response = client.post(
        "/api/v1/products/",
        json={
            "brand_id": brand_id,
            "name": "Test Product for Modules",
            "description": "A super test product",
            "price": 19.99
        },
        headers=auth_headers
    )
    assert product_response.status_code == 200
    product_id = product_response.json()["id"]

    # Test AdModule creation
    payload = {
        "product_id": product_id,
        "module_type": "intro",
        "content": "Are you tired of bugs?",
        "generation_metadata": {"hook_type": "Pain Activation", "format": "Question"},
        "performance_score": 0,
        "tags": ["testing"]
    }
    
    response = client.post(
        "/api/v1/ad-modules/",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["module_type"] == "intro"
    assert data["content"] == "Are you tired of bugs?"
    assert data["product_id"] == product_id
    
    module_id = data["id"]
    
    # Test GET modules
    get_response = client.get(f"/api/v1/ad-modules/?product_id={product_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert len(get_response.json()) > 0
    
    # Test GET single module
    single_response = client.get(f"/api/v1/ad-modules/{module_id}", headers=auth_headers)
    assert single_response.status_code == 200
    assert single_response.json()["id"] == module_id
    
    # Test PUT update module
    update_response = client.put(
        f"/api/v1/ad-modules/{module_id}",
        json={"content": "Updated content here"},
        headers=auth_headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["content"] == "Updated content here"
    
    # Test DELETE module
    del_response = client.delete(f"/api/v1/ad-modules/{module_id}", headers=auth_headers)
    assert del_response.status_code == 200
    
    # Verify deletion
    verify_response = client.get(f"/api/v1/ad-modules/{module_id}", headers=auth_headers)
    assert verify_response.status_code == 404
