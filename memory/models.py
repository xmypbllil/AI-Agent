"""Memory models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    kind: str
    payload: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class CacheEntry:
    key: str
    value: str
    created_at: datetime = field(default_factory=utc_now)
