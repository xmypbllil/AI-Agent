"""Minimal runnable agent built on the existing ActionGraph runtime."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
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
        observations.setdefault("expected_files", {})
        observations.setdefault("verified_files", {})

        graph = self.adapter.generate_plan(goal, observations)
        planned: list[str] = []
        for _ in range(self.max_steps):
            planned.extend(action.kind.value for action in graph.ordered())
            session.current_plan = tuple(planned)
            for action in graph.ordered():
                result = self.executor.execute(action)
                self._record(session, result)
                self._observe(observations, action, result)
            next_graph = self.adapter.decide_next_action(observations)
            if next_graph is not None:
                graph = next_graph
                continue
            if self._verified(session, observations):
                session.final_result = "verified"
                break
            break

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

    def _observe(self, observations: dict[str, Any], action: object, result: ActionResult) -> None:
        kind = action.kind if hasattr(action, "kind") else None
        pid = result.outputs.get("pid")
        if isinstance(pid, int):
            observations["last_pid"] = pid
        if kind is ActionKind.TYPE_TEXT and result.status is ActionStatus.SUCCEEDED:
            observations["typed"] = True
        if kind is ActionKind.WRITE_FILE and result.status is ActionStatus.SUCCEEDED:
            path = str(result.outputs.get("path"))
            inputs = action.inputs if hasattr(action, "inputs") else {}
            content = str(inputs.get("content", "")) if isinstance(inputs, Mapping) else ""
            expected_files = observations.setdefault("expected_files", {})
            if isinstance(expected_files, dict):
                expected_files[path] = content
        if kind is ActionKind.READ_FILE and result.status is ActionStatus.SUCCEEDED:
            path = str(result.outputs.get("path"))
            content = str(result.outputs.get("content", ""))
            expected_files = observations.get("expected_files")
            verified_files = observations.setdefault("verified_files", {})
            if isinstance(expected_files, dict) and isinstance(verified_files, dict):
                expected = expected_files.get(path)
                if expected is not None:
                    verified_files[path] = content == expected

    def _verified(self, session: AgentSession, observations: Mapping[str, Any]) -> bool:
        base_verified = bool(session.executed_actions) and not session.errors and all(
            result.status is ActionStatus.SUCCEEDED for result in session.executed_actions
        )
        expected_files = observations.get("expected_files")
        if isinstance(expected_files, dict) and expected_files:
            verified_files = observations.get("verified_files")
            if not isinstance(verified_files, dict):
                return False
            return base_verified and all(verified_files.get(path) is True for path in expected_files)
        return base_verified

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
        self.trace_path.write_text(
            json.dumps(json_safe(payload), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _trace_action(self, result: ActionResult) -> dict[str, Any]:
        payload = asdict(result)
        payload["started_at"] = result.started_at.isoformat()
        payload["finished_at"] = result.finished_at.isoformat() if result.finished_at else None
        return json_safe(payload)


def json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, tuple | list):
        return [json_safe(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, Path):
        return str(value)
    return value
