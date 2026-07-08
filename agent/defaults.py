"""Default agent components."""

from __future__ import annotations

from dataclasses import dataclass

from agent.models import AgentTask, PlanStep
from runtime.executor import PythonRuntime
from runtime.models import ExecutionRequest, ExecutionResult


@dataclass(frozen=True, slots=True)
class SingleStepPlanner:
    def plan(self, task: AgentTask) -> list[PlanStep]:
        return [PlanStep(code=task.instruction, description="model-authored python")]


@dataclass(frozen=True, slots=True)
class RuntimeExecutor:
    runtime: PythonRuntime

    def execute(self, step: PlanStep) -> ExecutionResult:
        return self.runtime.execute(ExecutionRequest(code=step.code))


@dataclass(frozen=True, slots=True)
class FailureCritic:
    def should_retry(self, result: ExecutionResult) -> bool:
        return not result.ok


@dataclass(frozen=True, slots=True)
class NoopReflection:
    def repair(self, step: PlanStep, result: ExecutionResult) -> PlanStep:
        return step
