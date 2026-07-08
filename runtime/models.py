"""Typed models for Python execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


class ExecutionStatus(StrEnum):
    """Final state of one runtime execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """Python code submitted to the runtime."""

    code: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Structured result returned by the runtime."""

    request_id: str
    status: ExecutionStatus
    stdout: str
    stderr: str
    value: Any | None = None
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status is ExecutionStatus.SUCCEEDED

    def readonly_metadata(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.metadata))
