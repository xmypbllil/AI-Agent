"""Platform-independent UI runtime contracts."""

from runtime.ui.locator import Locator
from runtime.ui.models import (
    UIControlType,
    UIElementBounds,
    UIElementIdentity,
    UIElementObservation,
    UIElementState,
    UITreeSnapshot,
)
from runtime.ui.ports import UIActionBackend, UIObservationBackend

__all__ = [
    "Locator",
    "UIActionBackend",
    "UIControlType",
    "UIElementBounds",
    "UIElementIdentity",
    "UIElementObservation",
    "UIElementState",
    "UIObservationBackend",
    "UITreeSnapshot",
]
