"""Development backend for file and terminal actions."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole


DEVELOPMENT_ACTIONS = {
    ActionKind.READ_FILE,
    ActionKind.WRITE_FILE,
    ActionKind.EDIT_FILE,
    ActionKind.SEARCH_FILES,
    ActionKind.RUN_COMMAND,
    ActionKind.CAPTURE_OUTPUT,
    ActionKind.WAIT_PROCESS,
}


@dataclass(frozen=True, slots=True)
class DevelopmentBackend:
    root: Path

    @property
    def name(self) -> str:
        return "development"

    @property
    def role(self) -> BackendRole:
        return BackendRole.MOCK

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_processes=True)

    def score(self, action: Action, context=None) -> BackendCandidate | None:
        if action.kind not in DEVELOPMENT_ACTIONS:
            return None
        return BackendCandidate(
            backend_name=self.name,
            score=0.9,
            reason="supports file and terminal development actions",
        )

    def execute(self, action: Action) -> ActionResult:
        started_at = datetime.now(tz=UTC)
        started = time.perf_counter()
        try:
            outputs = self._execute(action)
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.SUCCEEDED,
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
                duration_seconds=time.perf_counter() - started,
                backend_used=self.name,
                backend_score=0.9,
                backend_reason="executed file/terminal action through development backend",
                outputs=outputs,
            )
        except Exception as exc:  # noqa: BLE001 - backend maps runtime failures to ActionResult.
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.FAILED,
                started_at=started_at,
                finished_at=datetime.now(tz=UTC),
                duration_seconds=time.perf_counter() - started,
                backend_used=self.name,
                backend_score=0.9,
                backend_reason="supports file and terminal development actions",
                errors=(str(exc),),
            )

    def _execute(self, action: Action) -> dict[str, object]:
        if action.kind is ActionKind.READ_FILE:
            path = self._path(str(action.inputs["path"]))
            encoding = str(action.inputs["encoding"])
            return {"path": str(path), "content": path.read_text(encoding=encoding)}
        if action.kind is ActionKind.WRITE_FILE:
            path = self._path(str(action.inputs["path"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            encoding = str(action.inputs["encoding"])
            content = str(action.inputs["content"])
            path.write_text(content, encoding=encoding)
            return {"path": str(path), "bytes": len(content.encode(encoding))}
        if action.kind is ActionKind.EDIT_FILE:
            path = self._path(str(action.inputs["path"]))
            encoding = str(action.inputs["encoding"])
            content = path.read_text(encoding=encoding)
            old = str(action.inputs["old"])
            new = str(action.inputs["new"])
            if old not in content:
                raise ValueError(f"Text to replace not found in {path}")
            updated = content.replace(old, new, 1)
            path.write_text(updated, encoding=encoding)
            return {"path": str(path), "replacements": 1}
        if action.kind is ActionKind.SEARCH_FILES:
            root = self._path(str(action.inputs["root"]))
            pattern = str(action.inputs["pattern"])
            matches = [str(path) for path in root.rglob(pattern) if path.is_file()]
            return {"root": str(root), "pattern": pattern, "matches": matches}
        if action.kind in {ActionKind.RUN_COMMAND, ActionKind.CAPTURE_OUTPUT}:
            return self._run_command(action)
        if action.kind is ActionKind.WAIT_PROCESS:
            return {"pid": int(action.inputs["pid"]), "waited": False}
        raise ValueError(f"Unsupported development action: {action.kind}")

    def _run_command(self, action: Action) -> dict[str, object]:
        command = str(action.inputs["command"])
        cwd_value = action.inputs.get("cwd")
        cwd = self._path(str(cwd_value)) if cwd_value else self.root
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=action.timeout_seconds,
            check=False,
        )
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _path(self, value: str) -> Path:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root.resolve()):
            raise PermissionError(f"Path escapes development root: {resolved}")
        return resolved
