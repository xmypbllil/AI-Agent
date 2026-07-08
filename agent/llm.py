"""LLM adapter contracts and a local MVP adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from runtime.actions import ActionGraph, OpenApplicationAction, RunCommandAction, TypeTextAction
from runtime.observations import WindowLocator
from runtime.ui import Locator, UIControlType


class LLMAdapter(Protocol):
    """Provider-neutral planning interface for ActionGraph-based agents."""

    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph:
        """Create the first executable action graph for a goal."""

    def decide_next_action(self, observations: Mapping[str, Any]) -> ActionGraph | None:
        """Create the next action graph from runtime observations."""


@dataclass(slots=True)
class LocalMvpAdapter:
    """Deterministic adapter used by the local CLI when no provider is configured."""

    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph:
        normalized = goal.lower()
        if "notepad" in normalized or "\u0431\u043b\u043e\u043a\u043d\u043e\u0442" in normalized:
            return ActionGraph(actions=(OpenApplicationAction("notepad.exe"),))
        if normalized.startswith(("python ", "py ", "cmd ", "git ")):
            return ActionGraph(actions=(RunCommandAction(goal, cwd="."),))
        if (
            "compileall" in normalized
            or "validation" in normalized
            or "\u043f\u0440\u043e\u0432\u0435\u0440" in normalized
        ):
            return ActionGraph(
                actions=(
                    RunCommandAction("python -m compileall agent computer runtime tests evaluations", cwd="."),
                    RunCommandAction("python -m evaluations.run_validation", cwd=".", timeout_seconds=240.0),
                )
            )
        return ActionGraph(actions=(RunCommandAction(goal, cwd="."),))

    def decide_next_action(self, observations: Mapping[str, Any]) -> ActionGraph | None:
        goal = str(observations.get("goal", "")).lower()
        if "notepad" not in goal and "\u0431\u043b\u043e\u043a\u043d\u043e\u0442" not in goal:
            return None
        if observations.get("typed"):
            return None
        pid = observations.get("last_pid")
        if not isinstance(pid, int):
            return None
        text = str(observations.get("text") or "Hello Runtime")
        locator = Locator(
            control_type=UIControlType.EDIT,
            process=pid,
            window=WindowLocator(process_id=pid),
            visible=True,
            enabled=True,
        )
        return ActionGraph(actions=(TypeTextAction(locator=locator, text=text),))
