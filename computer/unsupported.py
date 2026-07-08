"""Unsupported capability adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

from computer.errors import CapabilityUnavailableError


@dataclass(frozen=True, slots=True)
class UnsupportedCapability:
    name: str

    def _raise(self) -> NoReturn:
        raise CapabilityUnavailableError(f"Capability is not configured: {self.name}")
