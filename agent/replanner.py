"""Goal-state driven replanning for the agent layer."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from runtime.actions import ActionGraph, ReadFileAction, TypeTextAction, WriteFileAction
from runtime.actions.models import Action, ActionKind, ActionResult
from runtime.observations import WindowLocator
from runtime.ui import Locator, UIControlType


@dataclass(frozen=True, slots=True)
class Replanner:
    """Build the next minimal ActionGraph from GoalState and observations."""

    def next_graph(
        self,
        goal: str,
        observations: Mapping[str, Any],
        previous_actions: tuple[ActionResult, ...],
        goal_state: Mapping[str, Any],
        evaluation_reason: str,
    ) -> ActionGraph | None:
        requirements = goal_state.get("requirements", {})
        if not isinstance(requirements, Mapping):
            return None
        attempted = attempted_signatures(previous_actions)

        files = requirements.get("files", ())
        if isinstance(files, tuple | list):
            graph = self._file_graph(tuple(str(item) for item in files), observations, attempted)
            if graph is not None:
                return graph

        if requirements.get("ui_text"):
            graph = self._ui_text_graph(observations, attempted)
            if graph is not None:
                return graph

        return None

    def _file_graph(
        self,
        files: tuple[str, ...],
        observations: Mapping[str, Any],
        attempted: set[tuple[str, tuple[tuple[str, str], ...]]],
    ) -> ActionGraph | None:
        expected_files = observations.get("expected_files", {})
        verified_files = observations.get("verified_files", {})
        read_files = observations.get("read_files", {})
        if not isinstance(expected_files, Mapping):
            expected_files = {}
        if not isinstance(verified_files, Mapping):
            verified_files = {}
        if not isinstance(read_files, Mapping):
            read_files = {}

        create_targets = created_file_targets_from_goal(observations.get("goal"))
        for path in files:
            expected = mapping_path_value(path, expected_files)
            verified = mapping_path_value(path, verified_files)
            read = mapping_path_value(path, read_files)
            if is_created_file_target(path, create_targets) and verified is not True:
                write = WriteFileAction(path, created_file_content(path, observations))
                read_action = ReadFileAction(path)
                actions = tuple(
                    action for action in (write, read_action) if action_signature(action) not in attempted
                )
                return ActionGraph(actions=actions) if actions else None
            if expected is not None and verified is not True:
                write = WriteFileAction(path, str(expected))
                read_action = ReadFileAction(path)
                actions = tuple(
                    action for action in (write, read_action) if action_signature(action) not in attempted
                )
                return ActionGraph(actions=actions) if actions else None
            if expected is None and read is not True:
                action = ReadFileAction(path)
                return None if action_signature(action) in attempted else ActionGraph(actions=(action,))
        return None

    def _ui_text_graph(
        self,
        observations: Mapping[str, Any],
        attempted: set[tuple[str, tuple[tuple[str, str], ...]]],
    ) -> ActionGraph | None:
        if observations.get("typed"):
            return None
        pid = observations.get("last_pid")
        if not isinstance(pid, int):
            return None
        text = observations.get("text")
        if not isinstance(text, str) or not text:
            return None
        locator = Locator(
            control_type=UIControlType.EDIT,
            process=pid,
            window=WindowLocator(process_id=pid),
            visible=True,
            enabled=True,
        )
        action = TypeTextAction(locator=locator, text=text)
        return None if action_signature(action) in attempted else ActionGraph(actions=(action,))


def attempted_signatures(results: tuple[ActionResult, ...]) -> set[tuple[str, tuple[tuple[str, str], ...]]]:
    signatures: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for result in results:
        telemetry = result.telemetry
        signature = telemetry.get("action_signature") if isinstance(telemetry, Mapping) else None
        if isinstance(signature, tuple):
            signatures.add(signature)
    return signatures


def action_signature(action: Action) -> tuple[str, tuple[tuple[str, str], ...]]:
    return (
        action.kind.value,
        tuple(sorted((str(key), str(value)) for key, value in action.inputs.items())),
    )


def mapping_path_value(path: str, values: Mapping[str, Any]) -> Any:
    normalized = path.replace("/", "\\").lower()
    for key, value in values.items():
        key_text = str(key).replace("/", "\\").lower()
        if key_text == normalized or key_text.endswith(f"\\{normalized}"):
            return value
    return None


def created_file_targets_from_goal(goal: Any) -> tuple[str, ...]:
    if not isinstance(goal, str):
        return ()

    matches = re.findall(
        r"(?:create|создай)\s+([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)",
        goal,   
        flags=re.IGNORECASE,
    )

    return tuple(matches)


def is_created_file_target(path: str, targets: tuple[str, ...]) -> bool:
    normalized = path.replace("/", "\\").lower()
    for target in targets:
        normalized_target = target.replace("/", "\\").lower()
        if normalized == normalized_target or normalized.endswith(f"\\{normalized_target}"):
            return True
    return False


def created_file_content(path: str, observations: Mapping[str, Any] | None = None) -> str:
    title = path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

    if observations:
        read_contents = observations.get("read_contents")
        if isinstance(read_contents, Mapping):
            texts = []
            for content in read_contents.values():
                if isinstance(content, str) and content.strip():
                    texts.append("\n".join(content.splitlines()[:5]))

            if texts:
                body = "\n\n---\n\n".join(texts)
                return f"# {title}\n\n{body}\n"

    return f"# {title}\n\nCreated by the agent replanner.\n"
