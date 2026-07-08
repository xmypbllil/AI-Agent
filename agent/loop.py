"""Agent loop orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from agent.models import AgentTask
from agent.ports import Critic, Executor, Planner, Reflection
from runtime.models import ExecutionResult


@dataclass(frozen=True, slots=True)
class AgentLoop:
    planner: Planner
    executor: Executor
    critic: Critic
    reflection: Reflection
    max_retries: int = 3

    def run(self, task: AgentTask) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        for step in self.planner.plan(task):
            current = step
            for _ in range(self.max_retries + 1):
                result = self.executor.execute(current)
                results.append(result)
                if not self.critic.should_retry(result):
                    break
                current = self.reflection.repair(current, result)
        return results
