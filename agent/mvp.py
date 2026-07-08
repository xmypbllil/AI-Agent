"""Minimal runnable agent built on the existing ActionGraph runtime."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from agent.llm import LLMAdapter
from agent.models import AgentSession
from runtime.actions.engine import ActionExecutor
from runtime.actions.models import ActionKind, ActionResult, ActionStatus


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    goal: str
    session: AgentSession
    trace_path: Path

    @property
    def verified(self) -> bool:
        return self.session.final_result == "verified"


@dataclass(slots=True)
class AgentRunner:
    adapter: LLMAdapter
    executor: ActionExecutor
    trace_path: Path = Path("evaluations") / "last-agent-cli-trace.json"
    max_steps: int = 5

    def run(self, goal: str, context: Mapping[str, Any] | None = None) -> AgentRunResult:
        started = time.perf_counter()
        session = AgentSession(goal=goal)
        observations: dict[str, Any] = {"goal": goal, **dict(context or {})}

        graph = self.adapter.generate_plan(goal, observations)
        for _ in range(self.max_steps):
            session.current_plan = tuple(action.kind.value for action in graph.ordered())
            for action in graph.ordered():
                result = self.executor.execute(action)
                self._record(session, result)
                self._observe(observations, action.kind, result)
            if self._verified(session):
                session.final_result = "verified"
                break
            next_graph = self.adapter.decide_next_action(observations)
            if next_graph is None:
                break
            graph = next_graph

        if session.final_result is None:
            session.final_result = "failed"
        self._write_trace(session, started)
        return AgentRunResult(goal=goal, session=session, trace_path=self.trace_path)

    def _record(self, session: AgentSession, result: ActionResult) -> None:
        session.executed_actions.append(result)
        if result.observations:
            session.observations.append(result.observations)
        if result.status is not ActionStatus.SUCCEEDED:
            session.errors.extend(result.errors or ("action failed",))
        if result.outputs.get("exit_code") not in (None, 0):
            session.errors.append(f"command exited with {result.outputs['exit_code']}")

    def _observe(self, observations: dict[str, Any], kind: ActionKind, result: ActionResult) -> None:
        pid = result.outputs.get("pid")
        if isinstance(pid, int):
            observations["last_pid"] = pid
        if kind is ActionKind.TYPE_TEXT and result.status is ActionStatus.SUCCEEDED:
            observations["typed"] = True

    def _verified(self, session: AgentSession) -> bool:
        return bool(session.executed_actions) and not session.errors and all(
            result.status is ActionStatus.SUCCEEDED for result in session.executed_actions
        )

    def _write_trace(self, session: AgentSession, started: float) -> None:
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "goal": session.goal,
            "prompt": getattr(self.adapter, "last_prompt", {}),
            "llm_plan": getattr(self.adapter, "last_plan", {}),
            "plan": list(session.current_plan),
            "final_result": session.final_result,
            "duration": time.perf_counter() - started,
            "actions": [self._trace_action(result) for result in session.executed_actions],
            "observations": [dict(item) for item in session.observations],
            "errors": list(session.errors),
        }
        self.trace_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _trace_action(self, result: ActionResult) -> dict[str, Any]:
        payload = asdict(result)
        payload["started_at"] = result.started_at.isoformat()
        payload["finished_at"] = result.finished_at.isoformat() if result.finished_at else None
        return payload
