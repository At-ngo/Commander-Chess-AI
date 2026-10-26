def test_create_game_session(client):
    payload = {
        "mode": "HUMAN_VS_AI",
        "player_side": "RED",
        "time_limit_seconds": 1800,
    }
    response = client.post("/api/v1/games", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "game_id" in data
    assert data["status"] == "IN_PROGRESS"
    assert data["side_to_move"] == "RED"
    assert len(data["pieces"]) == 38
    assert len(data["legal_actions"]) > 0


def test_get_game_state(client):
    # Create game first
    create_res = client.post("/api/v1/games", json={"mode": "HUMAN_VS_HUMAN"})
    game_id = create_res.json()["game_id"]

    # Query game
    get_res = client.get(f"/api/v1/games/{game_id}")
    assert get_res.status_code == 200
    assert get_res.json()["game_id"] == game_id


def test_execute_legal_action(client):
    create_res = client.post("/api/v1/games", json={"mode": "HUMAN_VS_HUMAN"})
    game_data = create_res.json()
    game_id = game_data["game_id"]

    # Pick first legal action
    first_action = game_data["legal_actions"][0]
    action_payload = {
        "action_type": first_action["action_type"],
        "piece_id": first_action["piece_id"],
        "to_pos": first_action["to_pos"],
        "state_version": game_data["state_version"],
    }

    action_res = client.post(f"/api/v1/games/{game_id}/actions", json=action_payload)
    assert action_res.status_code == 200
    res_data = action_res.json()
    assert res_data["state_version"] == 2
    assert "event" in res_data
    assert res_data["game_state"]["side_to_move"] == "BLUE"


def test_resign_game(client):
    create_res = client.post("/api/v1/games", json={"mode": "HUMAN_VS_AI"})
    game_id = create_res.json()["game_id"]

    resign_res = client.post(f"/api/v1/games/{game_id}/resign", json={"side": "RED"})
    assert resign_res.status_code == 200
    data = resign_res.json()
    assert data["status"] == "GAME_OVER"
    assert data["result"]["winner"] == "BLUE"
    assert data["result"]["reason"] == "RESIGNATION"


def test_draw_game(client):
    create_res = client.post("/api/v1/games", json={"mode": "HUMAN_VS_AI"})
    game_id = create_res.json()["game_id"]

    draw_res = client.post(f"/api/v1/games/{game_id}/draw", json={"side": "RED", "action": "OFFER"})
    assert draw_res.status_code == 200
    data = draw_res.json()
    assert data["status"] == "GAME_OVER"
    assert data["result"]["winner"] == "DRAW"
    assert data["result"]["reason"] == "MUTUAL_DRAW"
