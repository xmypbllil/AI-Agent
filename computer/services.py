"""Windows service capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Services(UnsupportedCapability):
    name: str = "services"

    def list(self) -> list[str]:
        self._raise()
