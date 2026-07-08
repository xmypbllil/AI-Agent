"""Python package inspection capability."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata


@dataclass(frozen=True, slots=True)
class Packages:
    def list(self) -> list[str]:
        return sorted(distribution.metadata["Name"] for distribution in metadata.distributions())
