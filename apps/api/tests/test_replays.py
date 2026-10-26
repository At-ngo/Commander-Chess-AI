def test_list_replays(client):
    response = client.get("/api/v1/replays")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_export_replay(client):
    response = client.post("/api/v1/replays/rep_sample_001/export")
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "COTULENH-NOTATION"
    assert '[Format "COTULENH-NOTATION"]' in data["content"]
