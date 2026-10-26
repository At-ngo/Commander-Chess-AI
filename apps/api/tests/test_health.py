def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["docs"] == "/docs"


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "uptime_seconds" in data


def test_version_contract(client):
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert data["contract_version"] == "1.0"
    assert data["mode"] == "TOTAL_FORCE"
