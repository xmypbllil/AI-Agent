"""Observation query models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class ObservationKind(StrEnum):
    PROCESS_LIST = "process_list"
    PROCESS_FIND = "process_find"
    PROCESS_STATUS = "process_status"
    WINDOW_LIST = "window_list"
    WINDOW_ACTIVE = "window_active"
    WINDOW_FIND = "window_find"


@dataclass(frozen=True, slots=True)
class WindowLocator:
    title: str | None = None
    process_id: int | None = None
    process_name: str | None = None
    class_name: str | None = None


@dataclass(frozen=True, slots=True)
class ObservationQuery:
    kind: ObservationKind
    inputs: Mapping[str, Any] = field(default_factory=dict)
    query_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, slots=True)
class ProcessQuery(ObservationQuery):
    def __init__(self, kind: ObservationKind, name: str | None = None, pid: int | None = None) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "inputs", {"name": name, "pid": pid})
        object.__setattr__(self, "query_id", str(uuid4()))


@dataclass(frozen=True, slots=True)
class WindowQuery(ObservationQuery):
    def __init__(self, kind: ObservationKind, locator: WindowLocator | None = None) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "inputs", {"locator": locator})
        object.__setattr__(self, "query_id", str(uuid4()))


@dataclass(frozen=True, slots=True)
class ObservationResult:
    query_id: str
    backend_used: str | None
    backend_score: float
    backend_reason: str | None
    observations: tuple[Any, ...] = ()
    errors: tuple[str, ...] = ()
