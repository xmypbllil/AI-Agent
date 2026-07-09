"""LLM adapter contracts and a local MVP adapter."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from runtime.actions import (
    ActionGraph,
    ActionKind,
    EditFileAction,
    OpenApplicationAction,
    ReadFileAction,
    RunCommandAction,
    SearchFilesAction,
    WriteFileAction,
    WindowAction,
)
from runtime.observations import WindowLocator
from agent.replanner import Replanner


class LLMAdapter(Protocol):
    """Provider-neutral planning interface for ActionGraph-based agents."""

    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph:
        """Create the first executable action graph for a goal."""

    def decide_next_action(
        self,
        goal: str,
        observations: Mapping[str, Any],
        previous_actions: tuple[Any, ...],
        reason: str,
    ) -> ActionGraph | None:
        """Create the next action graph from runtime observations."""


@dataclass(slots=True)
class LocalMvpAdapter:
    """Deterministic adapter used by the local CLI when no provider is configured."""

    replanner: Replanner = Replanner()

    def generate_plan(self, goal: str, context: Mapping[str, Any]) -> ActionGraph:
        normalized = goal.lower()
        report_graph = project_report_graph_from_goal(goal)
        if report_graph is not None:
            return report_graph
        operation_graph = operation_graph_from_goal(goal)
        if operation_graph is not None:
            return operation_graph
        file_graph = file_graph_from_goal(goal)
        if file_graph is not None:
            return file_graph
        application_graph = application_graph_from_goal(goal)
        if application_graph is not None:
            return application_graph
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

    def decide_next_action(
        self,
        goal: str,
        observations: Mapping[str, Any],
        previous_actions: tuple[Any, ...],
        reason: str,
    ) -> ActionGraph | None:
        goal_state = observations.get("goal_state", {})
        return self.replanner.next_graph(
            goal=goal,
            observations=observations,
            previous_actions=previous_actions,
            goal_state=goal_state if isinstance(goal_state, Mapping) else {},
            evaluation_reason=reason,
        )


def text_from_goal(goal: str) -> str | None:
    markers = ("write ", "type ", "\u043d\u0430\u043f\u0438\u0448\u0438 ")
    for marker in markers:
        if marker in goal:
            value = goal.split(marker, 1)[1].strip()
            return value or None
    return None


def file_graph_from_goal(goal: str) -> ActionGraph | None:
    normalized = goal.lower()
    file_requested = (
        "file" in normalized
        or "файл" in normalized
        or normalized.startswith("read ")
        or normalized.startswith("прочитай ")
    )
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


def operation_graph_from_goal(goal: str) -> ActionGraph | None:
    normalized = goal.lower()
    if wants_current_directory(normalized):
        return ActionGraph(actions=(RunCommandAction("cd", cwd="."),))

    folder = folder_name_from_goal(goal)
    if folder is not None:
        return ActionGraph(actions=(RunCommandAction(f'cmd /c mkdir "{folder}"', cwd="."),))

    text = text_search_from_goal(goal)
    if text is not None:
        return ActionGraph(actions=(RunCommandAction(rg_command(text), cwd="."),))

    file_to_find = file_to_find_from_goal(goal)
    if file_to_find is not None:
        return ActionGraph(actions=(SearchFilesAction(file_to_find, "."),))

    edit_path = edit_file_path_from_goal(goal)
    if edit_path is not None:
        replacement = replacement_from_goal(goal)
        if replacement is not None:
            old, new = replacement
            return ActionGraph(actions=(EditFileAction(edit_path, old, new), ReadFileAction(edit_path)))
        return ActionGraph(actions=(ReadFileAction(edit_path),))
    
    read_paths = re.findall(r"(?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+", goal)
    if len(read_paths) > 1:
        return ActionGraph(
            actions=tuple(ReadFileAction(path) for path in read_paths)
        )

    read_path = read_path_from_goal(goal)
    if read_path is not None:
        return ActionGraph(actions=(ReadFileAction(read_path),))
        read_path = read_path_from_goal(goal)
    if read_path is not None:
        return ActionGraph(actions=(ReadFileAction(read_path),))


    return None


def application_graph_from_goal(goal: str) -> ActionGraph | None:
    normalized = goal.lower()
    if any(marker in normalized for marker in ("close ", "\u0437\u0430\u043a\u0440\u043e\u0439 ")):
        title = application_title_from_goal(normalized)
        if title is not None:
            return ActionGraph(
                actions=(
                    WindowAction(
                        ActionKind.CLOSE_WINDOW,
                        WindowLocator(class_name=title),
                    ),
                )
            )
    if any(marker in normalized for marker in ("open ", "\u043e\u0442\u043a\u0440\u043e\u0439 ")):
        target = application_target_from_goal(normalized)
        if target is not None:
            return ActionGraph(actions=(OpenApplicationAction(target),))
    return None


def application_target_from_goal(normalized_goal: str) -> str | None:
    if "paint" in normalized_goal:
        return "mspaint.exe"
    if "notepad" in normalized_goal or "\u0431\u043b\u043e\u043a\u043d\u043e\u0442" in normalized_goal:
        return "notepad.exe"
    return None


def application_title_from_goal(normalized_goal: str) -> str | None:
    if "paint" in normalized_goal:
        return "paint"
    if "notepad" in normalized_goal or "\u0431\u043b\u043e\u043a\u043d\u043e\u0442" in normalized_goal:
        return "Notepad"
    return None


def file_path_from_goal(goal: str) -> str | None:
    match = re.search(r"(?:file|\u0444\u0430\u0439\u043b)\s+([^\s]+)", goal, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'")


def read_path_from_goal(goal: str) -> str | None:
    normalized = goal.lower()
    if not (
        normalized.startswith("read ")
        or normalized.startswith("\u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0439 ")
    ):
        return None
    match = re.search(r"(?:read|\u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0439)\s+([^\s]+)", goal, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'")


def file_to_find_from_goal(goal: str) -> str | None:
    match = re.search(
        r"(?:find file|\u043d\u0430\u0439\u0434\u0438 \u0444\u0430\u0439\u043b)\s+([^\s]+)",
        goal,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'")


def text_search_from_goal(goal: str) -> str | None:
    match = re.search(
        r"(?:find text|\u043d\u0430\u0439\u0434\u0438 \u0442\u0435\u043a\u0441\u0442)\s+(.+?)\s+"
        r"(?:in project|\u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435)\b",
        goal,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'") or None


def edit_file_path_from_goal(goal: str) -> str | None:
    match = re.search(
        r"(?:edit file|change file|\u0438\u0437\u043c\u0435\u043d\u0438 \u0444\u0430\u0439\u043b)\s+([^\s]+)",
        goal,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'")


def replacement_from_goal(goal: str) -> tuple[str, str] | None:
    match = re.search(
        r"(?:replace|замени)\s+(.+?)\s+(?:with|на)\s+(.+)$",
        goal,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    old = match.group(1).strip(" \"'")
    new = match.group(2).strip(" \"'")
    if not old:
        return None
    return old, new


def folder_name_from_goal(goal: str) -> str | None:
    match = re.search(
        r"(?:create folder|создай папку)\s+([^\s]+)",
        goal,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group(1).strip(" .,:;\"'")


def wants_current_directory(normalized_goal: str) -> bool:
    return any(
        marker in normalized_goal
        for marker in (
            "show current folder",
            "show current directory",
            "pwd",
            "\u043f\u043e\u043a\u0430\u0436\u0438 \u0442\u0435\u043a\u0443\u0449\u0443\u044e \u043f\u0430\u043f\u043a\u0443",
            "\u043f\u043e\u043a\u0430\u0436\u0438 \u0442\u0435\u043a\u0443\u0449\u0443\u044e \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0438\u044e",
        )
    )


def rg_command(text: str) -> str:
    search_code = f"""
import pathlib
import shutil
import subprocess
import sys

query = {text!r}
rg = shutil.which("rg")
if rg is not None:
    raise SystemExit(subprocess.run([rg, "-i", query, "."]).returncode)

skip = {{".git", "__pycache__", ".pytest_cache"}}
found = False
for path in pathlib.Path(".").rglob("*"):
    if any(part in skip for part in path.parts) or not path.is_file():
        continue
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for line_number, line in enumerate(content.splitlines(), 1):
        if query.casefold() in line.casefold():
            print(f"{{path}}:{{line_number}}:{{line}}")
            found = True

raise SystemExit(0 if found else 1)
"""
    encoded = base64.b64encode(search_code.encode("utf-8")).decode("ascii")
    return f'python -c "import base64; exec(base64.b64decode({encoded!r}).decode())"'


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


def project_report_graph_from_goal(goal: str) -> ActionGraph | None:
    normalized = goal.lower()
    wants_project_analysis = any(
        marker in normalized
        for marker in (
            "analyze project",
            "\u043f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 \u043f\u0440\u043e\u0435\u043a\u0442",
        )
    )
    if not wants_project_analysis:
        return None
    path_match = re.search(r"([A-Za-z0-9_.-]+\.md)\b", goal)
    if path_match is None:
        return None
    path = path_match.group(1)
    return ActionGraph(
        actions=(
            WriteFileAction(path, ""),
            ReadFileAction(path),
        )
    )


def project_report_content() -> str:
    return "\n".join(
        (
            "# Project Report",
            "",
            "Desktop LLM Runtime is a modular Python project for executing ActionGraph tasks.",
            "",
            "Implemented areas:",
            "- agent: planning, CLI, provider adapters, and execution loop.",
            "- runtime: actions, backend selection, observations, and world model.",
            "- computer: public facade for desktop, files, processes, windows, and UI.",
            "- tests: unit and integration coverage for runtime and agent scenarios.",
            "",
            "Current focus: reliable local agent execution with verified traces.",
        )
    )
