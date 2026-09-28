"""End-to-end pipeline: init DB -> ingest seasons -> build state graph -> run discovery engine.

Usage: .venv/Scripts/python.exe scripts/run_pipeline.py 2022 2023
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import configure_logging, get_logger
from app.db import SessionLocal, init_db
from app.discovery.engine import run_discovery
from app.features.state_engine import build_football_states
from app.ingestion.pipeline import ingest_seasons
from app.models import Play

configure_logging()
logger = get_logger("scripts.run_pipeline")


def main(seasons: list[int]) -> None:
    t0 = time.time()
    init_db()
    db = SessionLocal()
    try:
        runs = ingest_seasons(db, seasons)
        for r in runs:
            logger.info(f"ingested season {r.snapshot_id}: {r.row_count} plays ({r.mode})")

        import polars as pl

        rows = [dict(r.__dict__) for r in db.query(Play).all()]
        for r in rows:
            r.pop("_sa_instance_state", None)
        plays = pl.DataFrame(rows)
        states = build_football_states(plays)
        dv = "nflverse:" + "+".join(str(s) for s in sorted(states["season"].unique().to_list()))

        from app.graph.state_graph import persist_graph

        n_nodes, n_edges = persist_graph(db, states, dv)
        logger.info(f"state graph: {n_nodes} nodes, {n_edges} transitions")

        discoveries = run_discovery(db)
        logger.info(f"discovery engine produced {len(discoveries)} validated discoveries")
        for d in discoveries:
            logger.info(f"  [{d.discovery_type}] {d.title} (adj_p={d.adjusted_p_value:.4f}, n={d.sample_size})")

        logger.info(f"pipeline finished in {time.time() - t0:.1f}s")
    finally:
        db.close()


if __name__ == "__main__":
    seasons = [int(s) for s in sys.argv[1:]] or [2023]
    main(seasons)
