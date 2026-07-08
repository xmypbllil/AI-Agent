"""Windows window driver."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

from computer.backends.windows.user32 import RECT, raise_last_error, user32
from computer.errors import ElementNotFoundError
from computer.models import Rect, WindowInfo, WindowState

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
WM_CLOSE = 0x0010


@dataclass(frozen=True, slots=True)
class WindowsWindowDriver:
    def list(self) -> list[WindowInfo]:
        windows: list[WindowInfo] = []

        def callback(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            info = self._info(hwnd)
            if info is None or not info.title:
                return True
            windows.append(info)
            return True

        if not user32.EnumWindows(EnumWindowsProc(callback), 0):
            raise_last_error("EnumWindows failed")
        return windows

    def activate(self, title: str) -> None:
        matches = self.find(title)
        if not matches:
            raise ElementNotFoundError(f"Window not found: {title}")
        self.activate_handle(matches[0].handle)

    def activate_handle(self, handle: int) -> None:
        self.restore(handle)
        user32.BringWindowToTop(int(handle))
        user32.SetActiveWindow(int(handle))
        user32.SetForegroundWindow(int(handle))

    def active(self) -> WindowInfo | None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        return self._info(int(hwnd))

    def find(self, title: str) -> list[WindowInfo]:
        expected = title.lower()
        return [window for window in self.list() if expected in window.title.lower()]

    def close(self, handle: int) -> None:
        if not user32.PostMessageW(int(handle), WM_CLOSE, 0, 0):
            raise_last_error("PostMessageW(WM_CLOSE) failed")

    def minimize(self, handle: int) -> None:
        if not user32.ShowWindow(int(handle), SW_SHOWMINIMIZED):
            raise_last_error("ShowWindow(SW_SHOWMINIMIZED) failed")

    def restore(self, handle: int) -> None:
        user32.ShowWindow(int(handle), SW_RESTORE)

    def rect(self, handle: int) -> Rect:
        rect = RECT()
        if not user32.GetWindowRect(int(handle), ctypes.byref(rect)):
            raise_last_error("GetWindowRect failed")
        return Rect(
            left=int(rect.left),
            top=int(rect.top),
            width=int(rect.right - rect.left),
            height=int(rect.bottom - rect.top),
        )

    def _info(self, hwnd: int) -> WindowInfo | None:
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        state = WindowState.NORMAL
        if user32.IsIconic(hwnd):
            state = WindowState.MINIMIZED
        elif user32.IsZoomed(hwnd):
            state = WindowState.MAXIMIZED
        return WindowInfo(
            handle=int(hwnd),
            title=buffer.value,
            rect=self.rect(hwnd),
            process_id=int(pid.value) if pid.value else None,
            class_name=class_name.value or None,
            state=state,
        )
