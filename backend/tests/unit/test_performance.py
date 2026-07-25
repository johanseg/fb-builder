def test_csv_performance_import_is_removed(client, auth_headers):
    response = client.post(
        "/api/v1/performance/import",
        files={"file": ("legacy.csv", b"Ad Name,Amount spent (USD)\n", "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 404
