"""UI Automation protocols."""

from __future__ import annotations

from typing import Protocol

from ui.models import ElementQuery, UiElement


class UiAutomation(Protocol):
    def find(self, query: ElementQuery) -> list[UiElement]:
        """Find elements."""

    def invoke(self, element: UiElement) -> None:
        """Invoke an element."""

    def set_value(self, element: UiElement, value: str) -> None:
        """Set ValuePattern value."""
