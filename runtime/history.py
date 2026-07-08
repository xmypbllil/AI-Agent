"""Runtime history contracts and in-memory implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from runtime.models import ExecutionResult


class ExecutionHistory(Protocol):
    def append(self, result: ExecutionResult) -> None:
        """Persist one execution result."""

    def list_recent(self, limit: int = 50) -> list[ExecutionResult]:
        """Return recent execution results."""


@dataclass(slots=True)
class InMemoryExecutionHistory:
    _items: list[ExecutionResult] = field(default_factory=list)

    def append(self, result: ExecutionResult) -> None:
        self._items.append(result)

    def list_recent(self, limit: int = 50) -> list[ExecutionResult]:
        return self._items[-limit:]
