"""Application launching capability."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from runtime.actions import OpenApplicationAction
from runtime.actions.engine import ActionExecutor


@dataclass(frozen=True, slots=True)
class Apps:
    action_executor: ActionExecutor | None = None

    def open(self, target: str) -> int:
        if self.action_executor is not None:
            result = self.action_executor.execute(OpenApplicationAction(target))
            process_id = result.outputs.get("pid")
            return int(process_id) if process_id is not None else 0
        process = subprocess.Popen(target, shell=True)  # noqa: S602 - desktop runtime command.
        return int(process.pid)
