"""Python environment capability."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Python:
    def executable(self) -> str:
        return sys.executable

    def version(self) -> str:
        return sys.version
