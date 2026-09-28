from __future__ import annotations

from app.evidence.evidence_engine import build_evidence
from app.models import Discovery, Evidence, Game, Play


def _make_play(db, game_id, play_num, desc):
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if game is None:
        game = Game(game_id=game_id, season=2023, week=1, home_team="AAA", away_team="BBB", dataset_version="test:1")
        db.add(game)
    play = Play(
        id=f"{game_id}_{play_num}",
        game_id=game_id,
        play_id=play_num,
        season=2023,
        week=1,
        play_type="pass",
        desc=desc,
        dataset_version="test:1",
    )
    db.add(play)
    return play


def test_discovery_to_evidence_round_trip_traces_exact_plays(db_session):
    db = db_session
    p1 = _make_play(db, "G1", 1.0, "1st play description")
    p2 = _make_play(db, "G1", 2.0, "2nd play description")
    db.commit()

    discovery = Discovery(
        discovery_type="anomaly",
        title="test discovery",
        description="test",
        sample_size=2,
        baseline={},
        observed={},
        effect_size=0.5,
        statistical_test="test",
        p_value=0.01,
        adjusted_p_value=0.02,
        confidence_interval=[0.1, 0.2],
        limitations="none",
        dataset_version="test:1",
        algorithm_version="1.0.0",
        feature_version="1.0.0",
    )
    db.add(discovery)
    db.flush()

    evidence_ids = build_evidence(
        db, discovery_id=discovery.id, play_ids=[p1.id, p2.id], source="nflverse", dataset_version="test:1"
    )
    discovery.evidence_ids = evidence_ids
    db.commit()

    # Round trip: given only the discovery, we can recover the exact underlying plays
    fetched = db.query(Discovery).filter(Discovery.id == discovery.id).first()
    assert len(fetched.evidence_ids) == 2
    evidences = db.query(Evidence).filter(Evidence.id.in_(fetched.evidence_ids)).all()
    descriptions = {e.description for e in evidences}
    assert descriptions == {"1st play description", "2nd play description"}
    assert all(e.discovery_id == discovery.id for e in evidences)
    assert all(e.dataset_version == "test:1" for e in evidences)


def test_build_evidence_caps_at_limit(db_session):
    db = db_session
    play_ids = []
    for i in range(30):
        p = _make_play(db, "G1", float(i), f"play {i}")
        play_ids.append(p.id)
    db.commit()

    evidence_ids = build_evidence(
        db, discovery_id=None, play_ids=play_ids, source="nflverse", dataset_version="test:1", limit=10
    )
    assert len(evidence_ids) == 10
