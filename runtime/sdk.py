"""SDK-level application/task/plan models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping
from uuid import uuid4

from runtime.actions.graph import ActionGraph


@dataclass(frozen=True, slots=True)
class Application:
    name: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Task:
    instruction: str
    task_id: str = field(default_factory=lambda: str(uuid4()))
    application: Application | None = None


@dataclass(frozen=True, slots=True)
class Plan:
    task: Task
    graph: ActionGraph
