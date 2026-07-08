"""Runtime observation models.

These models describe observed computer state without exposing platform objects as the primary
identity. Backend-specific handles may be stored in metadata for later resolution by that backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping


class ProcessStatus(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    EXITED = "exited"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Bounds:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    name: str


@dataclass(frozen=True, slots=True)
class WindowIdentity:
    title: str
    process_id: int | None = None
    class_name: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    identity: ProcessIdentity
    path: str | None = None
    started_at: datetime | None = None
    status: ProcessStatus = ProcessStatus.UNKNOWN
    observed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WindowObservation:
    identity: WindowIdentity
    bounds: Bounds | None = None
    visible: bool = True
    active: bool = False
    observed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)
