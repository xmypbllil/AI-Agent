"""Null UI Automation adapter."""

from __future__ import annotations

from dataclasses import dataclass

from ui.models import ElementQuery, UiElement


@dataclass(frozen=True, slots=True)
class NullUiAutomation:
    def find(self, query: ElementQuery) -> list[UiElement]:
        return []

    def invoke(self, element: UiElement) -> None:
        raise NotImplementedError("UI Automation adapter is not configured")

    def set_value(self, element: UiElement, value: str) -> None:
        raise NotImplementedError("UI Automation adapter is not configured")
