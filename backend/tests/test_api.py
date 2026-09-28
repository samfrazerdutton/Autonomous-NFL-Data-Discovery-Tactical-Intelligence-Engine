from __future__ import annotations

from app.models import Discovery, Game


def test_health(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_system_status_on_empty_db(api_client):
    resp = api_client.get("/system")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_games"] == 0
    assert body["n_discoveries"] == 0
    assert "mode" in body


def test_discoveries_empty_list(api_client):
    resp = api_client.get("/discoveries")
    assert resp.status_code == 200
    assert resp.json() == []


def test_discovery_not_found(api_client):
    resp = api_client.get("/discoveries/does-not-exist")
    assert resp.status_code == 404


def test_games_list_reflects_seeded_data(api_client, db_session):
    db_session.add(
        Game(game_id="G1", season=2023, week=1, home_team="AAA", away_team="BBB", dataset_version="test:1")
    )
    db_session.commit()
    resp = api_client.get("/games")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["game_id"] == "G1"


def test_discovery_detail_round_trip(api_client, db_session):
    d = Discovery(
        discovery_type="anomaly",
        title="t",
        description="d",
        sample_size=10,
        baseline={"pass_rate": 0.5},
        observed={"pass_rate": 0.8},
        effect_size=0.3,
        statistical_test="permutation test",
        p_value=0.01,
        adjusted_p_value=0.02,
        confidence_interval=[0.1, 0.2],
        limitations="none",
        dataset_version="test:1",
        algorithm_version="1.0.0",
        feature_version="1.0.0",
        teams=["AAA"],
    )
    db_session.add(d)
    db_session.commit()

    resp = api_client.get(f"/discoveries/{d.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "t"
    assert body["teams"] == ["AAA"]

    resp_list = api_client.get("/discoveries?discovery_type=anomaly")
    assert len(resp_list.json()) == 1
