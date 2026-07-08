"""Environment variable capability."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Environment:
    def get(self, name: str, default: str | None = None) -> str | None:
        return os.environ.get(name, default)

    def list(self) -> dict[str, str]:
        return dict(os.environ)
