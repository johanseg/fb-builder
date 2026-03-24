import pytest
import io
import uuid

def test_performance_import_and_kill_rule(client, auth_headers):
    # 1. Setup Brand and Product
    unique_id = str(uuid.uuid4())[:8]
    brand_response = client.post(
        "/api/v1/brands/",
        json={"name": f"Perf Brand {unique_id}", "industry": "Tech", "company_description": "Descr", "colors": {"primary": "#000", "secondary": "#111", "highlight": "#222"}, "tone_of_voice": "Pro"},
        headers=auth_headers
    )
    assert brand_response.status_code == 200, brand_response.json()
    brand_id = brand_response.json()["id"]

    product_response = client.post(
        "/api/v1/products/",
        json={"brand_id": brand_id, "name": f"Perf Product {unique_id}", "description": "Descr", "price": 10},
        headers=auth_headers
    )
    assert product_response.status_code == 200, product_response.json()
    product_id = product_response.json()["id"]

    # 2. Create 2 modules (one to kill, one to scale)
    mod_kill = client.post("/api/v1/ad-modules/", json={"product_id": product_id, "module_type": "intro", "content": "Kill me", "generation_metadata": {"hook_type": "Pain", "format": "Text"}, "performance_score": 0, "tags": []}, headers=auth_headers).json()
    mod_scale = client.post("/api/v1/ad-modules/", json={"product_id": product_id, "module_type": "bridge", "content": "Scale me", "generation_metadata": {"bridge_type": "Logic"}, "performance_score": 0, "tags": []}, headers=auth_headers).json()

    kill_id_frag = str(mod_kill["id"])[:6]
    scale_id_frag = str(mod_scale["id"])[:6]

    # 3. Create mock CSV
    # kill gets CompleteRegistration (score 0), scale gets InitiatesCheckout (score 4)
    # Both need >$50 spend to trigger the rules
    csv_content = f"""Ad Name,Amount spent (USD),CompleteRegistration,Leads,Contacts,AddsToCart,InitiatesCheckout,AddsPaymentInfo
I-PAIN-{kill_id_frag}_B-MEC,100.50,5,0,0,0,0,0
I-LOGIC-{scale_id_frag}_C-VAL,200.00,0,0,0,0,10,0
I-NOTHING_329fA,0.00,0,0,0,0,0,0
"""

    file_data = {"file": ("perf_export.csv", io.BytesIO(csv_content.encode('utf-8')), "text/csv")}

    # 4. Upload CSV
    upload_response = client.post(
        "/api/v1/performance/import",
        files=file_data,
        headers=auth_headers
    )
    
    assert upload_response.status_code == 200
    assert "Successfully processed CSV" in upload_response.json()["message"]

    # 5. Check Kill Rule Flags
    flags_response = client.get("/api/v1/performance/kill-rule", headers=auth_headers)
    assert flags_response.status_code == 200
    flags = flags_response.json()

    kill_flag = next((f for f in flags if f["module_id"] == mod_kill["id"]), None)
    scale_flag = next((f for f in flags if f["module_id"] == mod_scale["id"]), None)

    assert kill_flag is not None
    assert kill_flag["status"] == "KILL"
    assert kill_flag["score"] == 0
    assert kill_flag["spend"] == 100.5

    assert scale_flag is not None
    assert scale_flag["status"] == "SCALE"
    assert scale_flag["score"] == 4
    assert scale_flag["spend"] == 200.0
