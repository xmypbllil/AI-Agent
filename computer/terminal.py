"""Terminal command capability."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from computer.models import CommandResult


@dataclass(frozen=True, slots=True)
class Terminal:
    cwd: Path | None = None
    timeout_seconds: float = 60.0

    def run(self, command: str, timeout_seconds: float | None = None) -> CommandResult:
        completed = subprocess.run(
            command,
            cwd=self.cwd,
            capture_output=True,
            shell=True,
            text=True,
            timeout=timeout_seconds or self.timeout_seconds,
            check=False,
        )
        return CommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
