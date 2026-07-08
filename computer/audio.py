"""Audio capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Audio(UnsupportedCapability):
    name: str = "audio"

    def devices(self) -> list[str]:
        self._raise()
