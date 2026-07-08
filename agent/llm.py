"""LLM adapter contracts and a local MVP adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from runtime.actions import (
    ActionGraph,
    OpenApplicationAction,
    ReadFileAction,
    RunCommandAction,
    TypeTextAction,
    WriteFileAction,
)
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
        file_graph = file_graph_from_goal(goal)
        if file_graph is not None:
            return file_graph
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
        raw_goal = str(observations.get("goal", ""))
        normalized = raw_goal.lower()
        if "notepad" not in normalized and "\u0431\u043b\u043e\u043a\u043d\u043e\u0442" not in normalized:
            return None
        if observations.get("typed"):
            return None
        pid = observations.get("last_pid")
        if not isinstance(pid, int):
            return None
        text = str(observations.get("text") or text_from_goal(raw_goal) or "Hello Runtime")
        locator = Locator(
            control_type=UIControlType.EDIT,
            process=pid,
            window=WindowLocator(process_id=pid),
            visible=True,
            enabled=True,
        )
        return ActionGraph(actions=(TypeTextAction(locator=locator, text=text),))


def text_from_goal(goal: str) -> str | None:
    markers = ("write ", "type ", "\u043d\u0430\u043f\u0438\u0448\u0438 ")
    for marker in markers:
        if marker in goal:
            value = goal.split(marker, 1)[1].strip()
            return value or None
    return None


def file_graph_from_goal(goal: str) -> ActionGraph | None:
    normalized = goal.lower()
    file_requested = "file" in normalized or "\u0444\u0430\u0439\u043b" in normalized
    if not file_requested:
        return None

    path = file_path_from_goal(goal)
    if path is None:
        return None

    wants_write = any(
        marker in normalized
        for marker in (
            "create file",
            "write file",
            "\u0441\u043e\u0437\u0434\u0430\u0439 \u0444\u0430\u0439\u043b",
            "\u0437\u0430\u043f\u0438\u0448\u0438 \u0444\u0430\u0439\u043b",
        )
    )
    wants_read = any(
        marker in normalized
        for marker in (
            "read file",
            "check file",
            "\u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0439 \u0444\u0430\u0439\u043b",
            "\u043f\u0440\u043e\u0432\u0435\u0440\u044c \u0444\u0430\u0439\u043b",
            "\u043f\u0440\u043e\u0432\u0435\u0440\u044c \u0447\u0442\u043e",
        )
    )

    actions = []
    if wants_write:
        actions.append(WriteFileAction(path, file_content_from_goal(goal) or ""))
    if wants_read or wants_write:
        actions.append(ReadFileAction(path))
    if not actions:
        return None
    return ActionGraph(actions=tuple(actions))


def file_path_from_goal(goal: str) -> str | None:
    match = re.search(r"(?:file|\u0444\u0430\u0439\u043b)\s+([^\s]+)", goal, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'")


def file_content_from_goal(goal: str) -> str | None:
    markers = ("with text ", "\u0441 \u0442\u0435\u043a\u0441\u0442\u043e\u043c ")
    for marker in markers:
        index = goal.lower().find(marker)
        if index == -1:
            continue
        value = goal[index + len(marker):].strip()
        for separator in (" and ", " \u0438 "):
            if separator in value:
                value = value.split(separator, 1)[0].strip()
        return value.strip("\"'") or None
    return None
