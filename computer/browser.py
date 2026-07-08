"""Browser capability."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Browser:
    def open(self, url: str) -> bool:
        return webbrowser.open(url)
