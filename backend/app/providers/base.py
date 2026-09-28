"""Adapter interface every data provider implements.

A provider's only job is: fetch raw data for a season/week, persist it via the
ingestion raw store (for lineage), and return it as a list of dict rows keyed
by the *source's own* field names. Normalization into the common Play schema
happens downstream in app.providers.<name>.normalize -- providers never invent
fields that their source doesn't actually return.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class FetchResult:
    source: str
    endpoint: str
    snapshot_id: str
    retrieved_at: datetime
    rows: list[dict]


class Provider(ABC):
    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can be used right now (e.g. API key present)."""

    @abstractmethod
    def fetch_play_by_play(self, season: int) -> FetchResult:
        ...

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
