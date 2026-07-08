"""Git capability."""

from __future__ import annotations

from dataclasses import dataclass

from computer.models import CommandResult
from computer.terminal import Terminal


@dataclass(frozen=True, slots=True)
class Git:
    terminal: Terminal

    def status(self) -> CommandResult:
        return self.terminal.run("git status --short")

    def run(self, args: str) -> CommandResult:
        return self.terminal.run(f"git {args}")
