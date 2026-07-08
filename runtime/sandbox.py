"""Execution sandbox abstractions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class Sandbox(Protocol):
    def globals_for(self, injected: dict[str, object]) -> dict[str, Any]:
        """Build globals for a single execution."""


@dataclass(frozen=True, slots=True)
class LocalSandbox:
    """Process-local sandbox with restricted builtins.

    This is the first implementation boundary. The protocol allows replacing it with an
    out-of-process sandbox later without changing runtime callers.
    """

    allowed_builtins: dict[str, object] = field(default_factory=dict)

    def globals_for(self, injected: dict[str, object]) -> dict[str, Any]:
        safe_builtins = {
            "Exception": Exception,
            "False": False,
            "None": None,
            "True": True,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "print": print,
            "range": range,
            "str": str,
            "tuple": tuple,
        }
        safe_builtins.update(self.allowed_builtins)
        return {"__builtins__": safe_builtins, **injected}
