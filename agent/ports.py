"""Agent component protocols."""

from __future__ import annotations

from typing import Protocol

from agent.models import AgentTask, PlanStep
from runtime.models import ExecutionResult


class Planner(Protocol):
    def plan(self, task: AgentTask) -> list[PlanStep]:
        """Create executable plan steps."""


class Executor(Protocol):
    def execute(self, step: PlanStep) -> ExecutionResult:
        """Execute one plan step."""


class Critic(Protocol):
    def should_retry(self, result: ExecutionResult) -> bool:
        """Decide if a failed result should be repaired and retried."""


class Reflection(Protocol):
    def repair(self, step: PlanStep, result: ExecutionResult) -> PlanStep:
        """Produce a repaired step."""
