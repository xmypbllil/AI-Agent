"""Windows stdlib-backed desktop drivers."""

from computer.backends.windows.action_backend import Win32Backend
from computer.backends.windows.clipboard import WindowsClipboardDriver
from computer.backends.windows.keyboard import WindowsKeyboardDriver
from computer.backends.windows.mouse import WindowsMouseDriver
from computer.backends.windows.processes import WindowsProcessDriver
from computer.backends.windows.screen import WindowsScreenDriver
from computer.backends.windows.windows import WindowsWindowDriver

try:
    from computer.backends.windows.uia_backend import UIAObservationBackend
    from computer.backends.windows.uia_action_backend import UIAActionBackend
except ImportError:  # pragma: no cover - optional dependency.
    UIAObservationBackend = None  # type: ignore[assignment]
    UIAActionBackend = None  # type: ignore[assignment]

__all__ = [
    "WindowsClipboardDriver",
    "Win32Backend",
    "WindowsKeyboardDriver",
    "WindowsMouseDriver",
    "WindowsProcessDriver",
    "WindowsScreenDriver",
    "WindowsWindowDriver",
    "UIAObservationBackend",
    "UIAActionBackend",
]
