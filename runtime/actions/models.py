"""Action domain models.

Actions describe intent. They do not know which backend will execute them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping
from uuid import uuid4


class ActionKind(StrEnum):
    OPEN_APPLICATION = "open_application"
    LAUNCH_PROCESS = "launch_process"
    TERMINATE_PROCESS = "terminate_process"
    WAIT_PROCESS_STARTED = "wait_process_started"
    WAIT_PROCESS_FINISHED = "wait_process_finished"
    ACTIVATE_WINDOW = "activate_window"
    CLOSE_WINDOW = "close_window"
    MINIMIZE_WINDOW = "minimize_window"
    RESTORE_WINDOW = "restore_window"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    SEARCH_FILES = "search_files"
    RUN_COMMAND = "run_command"
    CAPTURE_OUTPUT = "capture_output"
    WAIT_PROCESS = "wait_process"


class ActionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 1
    delay_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    inputs: Mapping[str, Any]
    action_id: str = field(default_factory=lambda: str(uuid4()))
    outputs: Mapping[str, Any] = field(default_factory=dict)
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    rollback: str | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_seconds: float = 30.0
    telemetry: Mapping[str, Any] = field(default_factory=dict)
    screenshot_before: bytes | None = None
    screenshot_after: bytes | None = None


@dataclass(frozen=True, slots=True)
class OpenApplicationAction(Action):
    def __init__(
        self,
        target: str,
        action_id: str | None = None,
        timeout_seconds: float = 30.0,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        object.__setattr__(self, "kind", ActionKind.OPEN_APPLICATION)
        object.__setattr__(self, "inputs", {"target": target})
        object.__setattr__(self, "action_id", action_id or str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", retry_policy or RetryPolicy())
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class LaunchProcessAction(Action):
    def __init__(self, command: str, cwd: str | None = None, timeout_seconds: float = 30.0) -> None:
        object.__setattr__(self, "kind", ActionKind.LAUNCH_PROCESS)
        object.__setattr__(self, "inputs", {"command": command, "cwd": cwd})
        object.__setattr__(self, "action_id", str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", RetryPolicy())
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class ProcessAction(Action):
    def __init__(self, kind: ActionKind, pid: int | None = None, name: str | None = None, timeout_seconds: float = 30.0) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "inputs", {"pid": pid, "name": name})
        object.__setattr__(self, "action_id", str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", RetryPolicy())
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class WindowAction(Action):
    def __init__(self, kind: ActionKind, locator: object | None = None, timeout_seconds: float = 30.0) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "inputs", {"locator": locator})
        object.__setattr__(self, "action_id", str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", RetryPolicy())
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class ClickAction(Action):
    def __init__(self, locator: object, timeout_seconds: float = 30.0) -> None:
        object.__setattr__(self, "kind", ActionKind.CLICK)
        object.__setattr__(self, "inputs", {"locator": locator})
        object.__setattr__(self, "action_id", str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", RetryPolicy())
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class TypeTextAction(Action):
    def __init__(self, locator: object, text: str, timeout_seconds: float = 30.0) -> None:
        object.__setattr__(self, "kind", ActionKind.TYPE_TEXT)
        object.__setattr__(self, "inputs", {"locator": locator, "text": text})
        object.__setattr__(self, "action_id", str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", RetryPolicy())
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class ReadFileAction(Action):
    def __init__(self, path: str, encoding: str = "utf-8") -> None:
        self._init(ActionKind.READ_FILE, {"path": path, "encoding": encoding})

    def _init(self, kind: ActionKind, inputs: Mapping[str, Any]) -> None:
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "action_id", str(uuid4()))
        object.__setattr__(self, "outputs", {})
        object.__setattr__(self, "preconditions", ())
        object.__setattr__(self, "postconditions", ())
        object.__setattr__(self, "rollback", None)
        object.__setattr__(self, "retry_policy", RetryPolicy())
        object.__setattr__(self, "timeout_seconds", 30.0)
        object.__setattr__(self, "telemetry", {})
        object.__setattr__(self, "screenshot_before", None)
        object.__setattr__(self, "screenshot_after", None)


@dataclass(frozen=True, slots=True)
class WriteFileAction(ReadFileAction):
    def __init__(self, path: str, content: str, encoding: str = "utf-8") -> None:
        self._init(ActionKind.WRITE_FILE, {"path": path, "content": content, "encoding": encoding})


@dataclass(frozen=True, slots=True)
class EditFileAction(ReadFileAction):
    def __init__(self, path: str, old: str, new: str, encoding: str = "utf-8") -> None:
        self._init(ActionKind.EDIT_FILE, {"path": path, "old": old, "new": new, "encoding": encoding})


@dataclass(frozen=True, slots=True)
class SearchFilesAction(ReadFileAction):
    def __init__(self, pattern: str, root: str = ".") -> None:
        self._init(ActionKind.SEARCH_FILES, {"pattern": pattern, "root": root})


@dataclass(frozen=True, slots=True)
class RunCommandAction(ReadFileAction):
    def __init__(self, command: str, cwd: str | None = None, timeout_seconds: float = 60.0) -> None:
        self._init(ActionKind.RUN_COMMAND, {"command": command, "cwd": cwd})
        object.__setattr__(self, "timeout_seconds", timeout_seconds)


@dataclass(frozen=True, slots=True)
class CaptureOutputAction(ReadFileAction):
    def __init__(self, command: str, cwd: str | None = None, timeout_seconds: float = 60.0) -> None:
        self._init(ActionKind.CAPTURE_OUTPUT, {"command": command, "cwd": cwd})
        object.__setattr__(self, "timeout_seconds", timeout_seconds)


@dataclass(frozen=True, slots=True)
class WaitProcessAction(ReadFileAction):
    def __init__(self, pid: int, timeout_seconds: float = 30.0) -> None:
        self._init(ActionKind.WAIT_PROCESS, {"pid": pid})
        object.__setattr__(self, "timeout_seconds", timeout_seconds)


@dataclass(frozen=True, slots=True)
class ActionResult:
    action_id: str
    status: ActionStatus
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    finished_at: datetime | None = None
    duration_seconds: float = 0.0
    backend_used: str | None = None
    backend_score: float = 0.0
    backend_reason: str | None = None
    outputs: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    observations: Mapping[str, Any] = field(default_factory=dict)
    screenshots: Mapping[str, bytes] = field(default_factory=dict)
    telemetry: Mapping[str, Any] = field(default_factory=dict)

    @property
    def backend_name(self) -> str | None:
        return self.backend_used

    @property
    def confidence(self) -> float:
        return self.backend_score

    @property
    def error(self) -> str | None:
        return self.errors[0] if self.errors else None

    @property
    def execution_time_seconds(self) -> float:
        return self.duration_seconds
