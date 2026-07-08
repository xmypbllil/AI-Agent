"""UI Automation models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ControlType(StrEnum):
    BUTTON = "button"
    EDIT = "edit"
    WINDOW = "window"
    MENU_ITEM = "menu_item"
    LIST = "list"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class ElementQuery:
    name: str | None = None
    automation_id: str | None = None
    control_type: ControlType | None = None


@dataclass(frozen=True, slots=True)
class UiElement:
    name: str
    automation_id: str | None
    control_type: ControlType
