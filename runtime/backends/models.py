"""Backend capability and scoring models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BackendRole(StrEnum):
    UI_AUTOMATION = "ui_automation"
    WIN32 = "win32"
    ACCESSIBILITY = "accessibility"
    OCR = "ocr"
    VISION = "vision"
    MOCK = "mock"


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    supports_open_application: bool = False
    supports_click: bool = False
    supports_keyboard: bool = False
    supports_window_search: bool = False
    supports_text: bool = False
    supports_scroll: bool = False
    supports_drag: bool = False
    supports_tree: bool = False
    supports_pattern: bool = False
    supports_processes: bool = False
    supports_screen: bool = False
    supports_clipboard: bool = False


@dataclass(frozen=True, slots=True)
class BackendCandidate:
    backend_name: str
    score: float
    reason: str

    @property
    def confidence(self) -> float:
        return self.score
