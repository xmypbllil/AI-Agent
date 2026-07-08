"""Universal UI locator model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Pattern

from runtime.observations import WindowLocator
from runtime.ui.models import UIControlType


@dataclass(frozen=True, slots=True)
class Locator:
    automation_id: str | None = None
    name: str | None = None
    regex: str | Pattern[str] | None = None
    control_type: UIControlType | None = None
    class_name: str | None = None
    process: int | str | None = None
    window: WindowLocator | str | None = None
    parent: "Locator | None" = None
    children: tuple["Locator", ...] = ()
    index: int | None = None
    visible: bool | None = None
    enabled: bool | None = None
