"""ActionGraph-oriented agent session loop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent.models import AgentSession
from runtime.actions.engine import ActionExecutor
from runtime.actions.graph import ActionGraph
from runtime.actions.models import ActionResult, ActionStatus


Decision = Callable[[AgentSession], ActionGraph | None]
Verifier = Callable[[AgentSession], bool]


@dataclass(slots=True)
class ActionAgentLoop:
    executor: ActionExecutor
    decide_next: Decision
    verify: Verifier
    max_iterations: int = 5

    def run(self, goal: str) -> AgentSession:
        session = AgentSession(goal=goal)
        for _ in range(self.max_iterations):
            graph = self.decide_next(session)
            if graph is None:
                break
            session.current_plan = tuple(action.kind.value for action in graph.ordered())
            results = [self.executor.execute(action) for action in graph.ordered()]
            self._record(session, results)
            if self.verify(session):
                session.final_result = "verified"
                return session
        if session.final_result is None:
            session.final_result = "failed"
        return session

    def _record(self, session: AgentSession, results: list[ActionResult]) -> None:
        for result in results:
            session.executed_actions.append(result)
            if result.observations:
                session.observations.append(result.observations)
            if result.status is not ActionStatus.SUCCEEDED:
                session.errors.extend(result.errors or ("action failed",))
            if result.outputs.get("exit_code") not in (None, 0):
                session.errors.append(f"command exited with {result.outputs['exit_code']}")
