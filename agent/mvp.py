"""Minimal runnable agent built on the existing ActionGraph runtime."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from agent.llm import LLMAdapter
from agent.models import AgentSession
from runtime.actions.graph import ActionGraph
from runtime.actions.engine import ActionExecutor
from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.ui.engine import UIObservationExecutor
from runtime.ui.locator import Locator
from agent.replanner import action_signature, mapping_path_value


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    goal: str
    session: AgentSession
    trace_path: Path

    @property
    def verified(self) -> bool:
        return self.session.final_result == "verified"


@dataclass(frozen=True, slots=True)
class GoalEvaluation:
    achieved: bool
    reason: str
    completed: tuple[str, ...]
    pending: tuple[str, ...]
    state: Mapping[str, Any]


@dataclass(slots=True)
class GoalEvaluator:
    def evaluate(
        self,
        goal: str,
        observations: Mapping[str, Any],
        actions: list[ActionResult],
    ) -> GoalEvaluation:
        requirements = self._requirements(goal, observations, actions)
        completed: list[str] = []
        pending: list[str] = []

        if requirements["files"]:
            verified_files = observations.get("verified_files", {})
            read_files = observations.get("read_files", {})
            if isinstance(verified_files, Mapping) and isinstance(read_files, Mapping) and all(
                file_satisfied(path, verified_files, read_files) for path in requirements["files"]
            ):
                completed.append("files")
            else:
                pending.append("files")

        if requirements["ui_text"]:
            verified_ui_text = observations.get("verified_ui_text", {})
            if isinstance(verified_ui_text, Mapping) and verified_ui_text and all(
                value is True for value in verified_ui_text.values()
            ):
                completed.append("ui_text")
            else:
                pending.append("ui_text")

        if requirements["commands"]:
            command_results = observations.get("command_results", [])
            if isinstance(command_results, list) and command_results and all(
                item.get("exit_code") == 0 for item in command_results if isinstance(item, Mapping)
            ):
                completed.append("commands")
            else:
                pending.append("commands")

        if not requirements["files"] and not requirements["ui_text"] and not requirements["commands"]:
            if actions and not self._actions_ok(actions):
                pending.append("actions")
            elif actions:
                completed.append("actions")
            else:
                pending.append("plan")

        if not self._actions_ok(actions):
            pending.append("actions_failed")

        achieved = bool(completed) and not pending
        reason = "goal achieved" if achieved else f"pending: {', '.join(dict.fromkeys(pending))}"
        return GoalEvaluation(
            achieved=achieved,
            reason=reason,
            completed=tuple(dict.fromkeys(completed)),
            pending=tuple(dict.fromkeys(pending)),
            state={
                "requirements": requirements,
                "actions_ok": self._actions_ok(actions),
            },
        )

    def _requirements(
        self,
        goal: str,
        observations: Mapping[str, Any],
        actions: list[ActionResult],
    ) -> dict[str, Any]:
        expected_files = observations.get("expected_files", {})
        files = set(expected_files.keys()) if isinstance(expected_files, Mapping) else set()
        normalized = goal.lower()
        command_goal = normalized.startswith(("python ", "py ", "cmd ", "git "))
        if not command_goal:
            for path in expected_file_paths_from_goal(goal):
                files.add(path)
        ui_text = bool(observations.get("expected_ui_text")) or wants_ui_text_goal(normalized)
        commands = command_goal or any(result.outputs.get("command") is not None for result in actions)
        if "validation" in normalized or "compileall" in normalized:
            commands = True
        return {"files": tuple(sorted(files)), "ui_text": ui_text, "commands": commands}

    def _actions_ok(self, actions: list[ActionResult]) -> bool:
        return bool(actions) and all(
            result.status is ActionStatus.SUCCEEDED
            and result.outputs.get("exit_code") in (None, 0)
            for result in actions
        )


@dataclass(slots=True)
class AgentRunner:
    adapter: LLMAdapter
    executor: ActionExecutor
    ui_observation_executor: UIObservationExecutor | None = None
    trace_path: Path = Path("evaluations") / "last-agent-cli-trace.json"
    max_steps: int = 5
    evaluator: GoalEvaluator = field(default_factory=GoalEvaluator)

    def run(self, goal: str, context: Mapping[str, Any] | None = None) -> AgentRunResult:
        started = time.perf_counter()
        session = AgentSession(goal=goal)
        observations: dict[str, Any] = {"goal": goal, **dict(context or {})}
        observations.setdefault("expected_files", {})
        observations.setdefault("verified_files", {})
        observations.setdefault("expected_ui_text", {})
        observations.setdefault("verified_ui_text", {})
        observations.setdefault("observed_ui_text", {})
        observations.setdefault("command_results", [])
        observations.setdefault("read_files", {})
        expected_ui_text = ui_text_from_goal(goal)
        if expected_ui_text is not None:
            observations["text"] = expected_ui_text

        graph = self.adapter.generate_plan(goal, observations)
        planned: list[str] = []
        replans_count = 0
        evaluation = GoalEvaluation(False, "not evaluated", (), (), {})
        for _ in range(self.max_steps):
            ordered = graph.ordered()
            planned.extend(action.kind.value for action in ordered)
            session.current_plan = tuple(planned)
            for action in ordered:
                result = self._execute_action(action)
                self._record(session, result)
                self._observe(observations, action, result)

            evaluation = self.evaluator.evaluate(goal, observations, session.executed_actions)
            self._apply_evaluation(session, evaluation)
            observations["goal_state"] = evaluation.state
            if evaluation.achieved:
                session.final_result = "verified"
                break

            observations["goal"] = goal
            observations["previous_actions"] = [self._trace_action(item) for item in session.executed_actions]
            observations["evaluation_reason"] = evaluation.reason
            next_graph = self.adapter.decide_next_action(
                goal,
                observations,
                tuple(session.executed_actions),
                evaluation.reason,
            )
            if next_graph is None:
                next_graph = self.adapter.generate_plan(goal, observations)
            if not self._should_continue(next_graph, ordered):
                break
            replans_count += 1
            graph = next_graph

        if session.final_result is None:
            session.final_result = "failed"
            self._apply_evaluation(session, evaluation)
        self._write_trace(session, observations, evaluation, replans_count, started)
        return AgentRunResult(goal=goal, session=session, trace_path=self.trace_path)

    def _execute_action(self, action: Action) -> ActionResult:
        signature = action_signature(action)
        try:
            result = self.executor.execute(action)
        except Exception as exc:  # noqa: BLE001 - agent records executor failures.
            result = ActionResult(
                action_id=action.action_id,
                status=ActionStatus.FAILED,
                started_at=datetime.now(tz=UTC),
                finished_at=datetime.now(tz=UTC),
                errors=(f"not found: {exc}",),
            )
        return ActionResult(
            action_id=result.action_id,
            status=result.status,
            started_at=result.started_at,
            finished_at=result.finished_at,
            duration_seconds=result.duration_seconds,
            backend_used=result.backend_used,
            backend_score=result.backend_score,
            backend_reason=result.backend_reason,
            outputs=result.outputs,
            errors=result.errors,
            observations=result.observations,
            screenshots=result.screenshots,
            telemetry={**result.telemetry, "action_signature": signature},
        )

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
            inputs = action.inputs if hasattr(action, "inputs") else {}
            if isinstance(inputs, Mapping):
                locator = inputs.get("locator")
                text = str(inputs.get("text", ""))
                if isinstance(locator, Locator):
                    key = str(result.action_id)
                    expected_ui_text = observations.setdefault("expected_ui_text", {})
                    if isinstance(expected_ui_text, dict):
                        expected_ui_text[key] = {"locator": locator, "text": text}
                    verified_ui_text = observations.setdefault("verified_ui_text", {})
                    if isinstance(verified_ui_text, dict):
                        observed = self._read_ui_text(locator)
                        observed_ui_text = observations.setdefault("observed_ui_text", {})
                        if isinstance(observed_ui_text, dict):
                            observed_ui_text[key] = observed
                        verified_ui_text[key] = observed is not None and text in observed
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
            read_contents = observations.setdefault("read_contents", {})
            if isinstance(read_contents, dict):
                read_contents[path] = content
            read_files = observations.setdefault("read_files", {})
            if isinstance(read_files, dict):
                read_files[path] = True
            expected_files = observations.get("expected_files")
            verified_files = observations.setdefault("verified_files", {})
            if isinstance(expected_files, dict) and isinstance(verified_files, dict):
                expected = expected_files.get(path)
                if expected is not None:
                    verified_files[path] = content == expected
        if kind is ActionKind.RUN_COMMAND:
            command_results = observations.setdefault("command_results", [])
            if isinstance(command_results, list):
                command_results.append(
                    {
                        "command": result.outputs.get("command"),
                        "exit_code": result.outputs.get("exit_code"),
                        "stdout": result.outputs.get("stdout"),
                    }
                )

    def _apply_evaluation(self, session: AgentSession, evaluation: GoalEvaluation) -> None:
        session.completed_goals = list(evaluation.completed)
        session.pending_goals = list(evaluation.pending)
        session.reasoning.append(evaluation.reason)
        session.goal_state = evaluation.state

    def _should_continue(self, next_graph: ActionGraph, previous_actions: list[Action]) -> bool:
        next_signature = tuple(action_signature(action) for action in next_graph.ordered())
        previous_signature = tuple(action_signature(action) for action in previous_actions)
        return bool(next_signature) and next_signature != previous_signature

    def _read_ui_text(self, locator: Locator) -> str | None:
        if self.ui_observation_executor is None:
            return None
        return self.ui_observation_executor.text(locator)

    def _write_trace(
        self,
        session: AgentSession,
        observations: Mapping[str, Any],
        evaluation: GoalEvaluation,
        replans_count: int,
        started: float,
    ) -> None:
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "goal": session.goal,
            "prompt": getattr(self.adapter, "last_prompt", {}),
            "llm_plan": getattr(self.adapter, "last_plan", {}),
            "plan": list(session.current_plan),
            "final_result": session.final_result,
            "goal_state": session.goal_state,
            "evaluation_reason": evaluation.reason,
            "replans_count": replans_count,
            "duration": time.perf_counter() - started,
            "actions": [self._trace_action(result) for result in session.executed_actions],
            "observations": [dict(item) for item in session.observations],
            "verification": {
                "expected_files": observations.get("expected_files", {}),
                "verified_files": observations.get("verified_files", {}),
                "expected_ui_text": observations.get("expected_ui_text", {}),
                "observed_ui_text": observations.get("observed_ui_text", {}),
                "verified_ui_text": observations.get("verified_ui_text", {}),
            },
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


def expected_file_paths_from_goal(goal: str) -> tuple[str, ...]:
    matches = re.findall(r"([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)\b", goal)
    return tuple(dict.fromkeys(matches))


def file_satisfied(
    path: str,
    verified_files: Mapping[str, Any],
    read_files: Mapping[str, Any],
) -> bool:
    return mapping_path_value(path, verified_files) is True or mapping_path_value(path, read_files) is True


def wants_ui_text_goal(normalized_goal: str) -> bool:
    app_requested = "notepad" in normalized_goal or "\u0431\u043b\u043e\u043a\u043d\u043e\u0442" in normalized_goal
    text_requested = any(
        marker in normalized_goal
        for marker in ("write ", "type ", "\u043d\u0430\u043f\u0438\u0448\u0438 ")
    )
    return app_requested and text_requested


def ui_text_from_goal(goal: str) -> str | None:
    normalized = goal.lower()
    markers = ("write ", "type ", "\u043d\u0430\u043f\u0438\u0448\u0438 ")
    for marker in markers:
        position = normalized.find(marker)
        if position >= 0:
            text = goal[position + len(marker) :].strip()
            return text or None
    return None
