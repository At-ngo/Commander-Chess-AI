def test_list_agents(client):
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) >= 1
    agent_ids = [a["agent_id"] for a in data["agents"]]
    assert "random_agent" in agent_ids


def test_get_agent_detail(client):
    response = client.get("/api/v1/agents/random_agent")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"]["agent_id"] == "random_agent"
    assert data["agent"]["status"] == "READY"


def test_get_nonexistent_agent(client):
    response = client.get("/api/v1/agents/unknown_agent_xyz")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "AGENT_NOT_FOUND"
