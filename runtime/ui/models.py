"""Platform-independent UI observation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping


class UIControlType(StrEnum):
    WINDOW = "window"
    BUTTON = "button"
    EDIT = "edit"
    TEXT = "text"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    LIST = "list"
    LIST_ITEM = "list_item"
    TREE = "tree"
    TREE_ITEM = "tree_item"
    COMBO_BOX = "combo_box"
    CHECK_BOX = "check_box"
    RADIO_BUTTON = "radio_button"
    TAB = "tab"
    TAB_ITEM = "tab_item"
    PANE = "pane"
    DOCUMENT = "document"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class UIElementBounds:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class UIElementState:
    visible: bool | None = None
    enabled: bool | None = None
    focused: bool | None = None
    selected: bool | None = None
    expanded: bool | None = None


@dataclass(frozen=True, slots=True)
class UIElementIdentity:
    stable_id: str
    automation_id: str | None = None
    name: str | None = None
    class_name: str | None = None
    control_type: UIControlType = UIControlType.UNKNOWN
    process_id: int | None = None
    window_title: str | None = None


@dataclass(frozen=True, slots=True)
class UIElementObservation:
    identity: UIElementIdentity
    bounds: UIElementBounds | None = None
    state: UIElementState = field(default_factory=UIElementState)
    text: str | None = None
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    observed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UITreeSnapshot:
    root_id: str | None
    elements: Mapping[str, UIElementObservation]
    captured_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)
