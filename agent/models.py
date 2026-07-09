"""Agent loop models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import uuid4

from runtime.actions.models import ActionResult


@dataclass(frozen=True, slots=True)
class AgentTask:
    instruction: str
    task_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, slots=True)
class PlanStep:
    code: str
    description: str


@dataclass(slots=True)
class AgentSession:
    goal: str
    current_plan: tuple[str, ...] = ()
    executed_actions: list[ActionResult] = field(default_factory=list)
    observations: list[Mapping[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    final_result: str | None = None
    completed_goals: list[str] = field(default_factory=list)
    pending_goals: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    goal_state: Mapping[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.final_result is not None and not self.errors
