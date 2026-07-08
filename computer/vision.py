"""Computer vision bridge capability."""

from __future__ import annotations

from dataclasses import dataclass

from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Vision(UnsupportedCapability):
    name: str = "vision"

    def find_text(self, text: str) -> list[object]:
        self._raise()
