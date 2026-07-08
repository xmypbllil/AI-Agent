"""Windows mouse driver."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

from computer.backends.windows.user32 import raise_last_error, user32
from computer.models import MouseButton, Point

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

BUTTON_FLAGS = {
    MouseButton.LEFT: (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    MouseButton.RIGHT: (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    MouseButton.MIDDLE: (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


@dataclass(frozen=True, slots=True)
class WindowsMouseDriver:
    def move(self, point: Point) -> None:
        if not user32.SetCursorPos(point.x, point.y):
            raise_last_error("SetCursorPos failed")

    def click(self, point: Point | None = None, button: MouseButton = MouseButton.LEFT) -> None:
        if point is not None:
            self.move(point)
        down, up = BUTTON_FLAGS[button]
        user32.mouse_event(down, 0, 0, 0, ctypes.c_ulonglong(0))
        user32.mouse_event(up, 0, 0, 0, ctypes.c_ulonglong(0))
