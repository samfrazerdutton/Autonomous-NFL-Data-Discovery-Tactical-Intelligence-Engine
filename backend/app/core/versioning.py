"""Reproducibility identifiers attached to every ingestion run and Discovery.

DATASET_VERSION is resolved per ingestion run (identifies exactly which source
snapshot produced the plays a Discovery is built from). CODE_VERSION is the git
commit of the running code. FEATURE_VERSION / ALGORITHM_VERSION are constants
bumped by hand whenever the corresponding logic changes in a way that would
change results for the same input data.
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

FEATURE_VERSION = "1.0.0"

ALGORITHM_VERSIONS = {
    "clustering": "1.0.0",
    "anomaly": "1.0.0",
    "changepoint": "1.0.0",
    "sequence": "1.0.0",
    "state_graph": "1.0.0",
}


@lru_cache(maxsize=1)
def code_version() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
        return sha.decode().strip()
    except Exception:
        return "unversioned"


def dataset_version(source: str, snapshot_id: str) -> str:
    """e.g. dataset_version('nflverse', '2023') -> 'nflverse:2023'"""
    return f"{source}:{snapshot_id}"
