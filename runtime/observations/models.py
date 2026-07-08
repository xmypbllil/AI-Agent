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
    parent_pid: int | None = None
    session_id: int | None = None
    application_runtime_id: str | None = None


@dataclass(frozen=True, slots=True)
class WindowIdentity:
    title: str
    process_id: int | None = None
    class_name: str | None = None
    runtime_window_id: str | None = None
    application_runtime_id: str | None = None
    app_user_model_id: str | None = None
    package_family_name: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    identity: ProcessIdentity
    path: str | None = None
    started_at: datetime | None = None
    status: ProcessStatus = ProcessStatus.UNKNOWN
    observed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)
    command_line: str | None = None
    parent_pid: int | None = None
    package_family_name: str | None = None
    app_user_model_id: str | None = None
    application_runtime_id: str | None = None


@dataclass(frozen=True, slots=True)
class WindowObservation:
    identity: WindowIdentity
    bounds: Bounds | None = None
    visible: bool = True
    active: bool = False
    observed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)
    owner: "WindowOwnershipObservation | None" = None
    z_order: int | None = None
    display_id: str | None = None


@dataclass(frozen=True, slots=True)
class ApplicationIdentity:
    name: str
    executable: str | None = None
    path: str | None = None
    package_family_name: str | None = None
    app_user_model_id: str | None = None
    publisher: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ApplicationRuntimeIdentity:
    runtime_id: str
    application: ApplicationIdentity
    root_process_id: int | None = None
    process_ids: tuple[int, ...] = ()
    window_ids: tuple[WindowIdentity, ...] = ()
    started_at: datetime | None = None
    correlation_keys: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProcessTreeObservation:
    root: ProcessIdentity
    processes: tuple[ProcessObservation, ...]
    parent_by_pid: Mapping[int, int]
    observed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WindowOwnershipObservation:
    window: WindowIdentity
    application_runtime_id: str | None = None
    process_id: int | None = None
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
