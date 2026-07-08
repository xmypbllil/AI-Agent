"""Windows registry capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Registry(UnsupportedCapability):
    name: str = "registry"

    def read(self, key: str, value: str) -> str:
        self._raise()
