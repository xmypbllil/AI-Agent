"""Computer capability protocols."""

from __future__ import annotations

from typing import Protocol

from computer.models import MouseButton, Point, ProcessInfo, Rect, WindowInfo


class ProcessDriver(Protocol):
    def list(self) -> list[ProcessInfo]:
        """List processes."""

    def start(self, command: str, cwd: str | None = None) -> ProcessInfo:
        """Start a process."""

    def terminate(self, pid: int, force: bool = False) -> None:
        """Terminate a process."""

    def find_by_name(self, name: str) -> list[ProcessInfo]:
        """Find processes by executable name."""

    def wait_started(self, name: str, timeout_seconds: float = 30.0) -> ProcessInfo:
        """Wait until a process with name appears."""

    def wait_exited(self, pid: int, timeout_seconds: float = 30.0) -> None:
        """Wait until a process exits."""


class MouseDriver(Protocol):
    def move(self, point: Point) -> None:
        """Move pointer to a screen point."""

    def click(self, point: Point | None = None, button: MouseButton = MouseButton.LEFT) -> None:
        """Click a mouse button."""

    def drag(self, start: Point, end: Point, button: MouseButton = MouseButton.LEFT) -> None:
        """Drag from one point to another."""

    def scroll(self, amount: int, point: Point | None = None) -> None:
        """Scroll the mouse wheel."""


class KeyboardDriver(Protocol):
    def write(self, text: str) -> None:
        """Type text."""

    def press(self, key: str) -> None:
        """Press a key."""

    def hotkey(self, *keys: str) -> None:
        """Press a key chord."""

    def hold(self, key: str) -> None:
        """Hold a key down."""

    def release(self, key: str) -> None:
        """Release a held key."""


class ScreenDriver(Protocol):
    def capture(self, region: Rect | None = None) -> bytes:
        """Capture screen bytes."""

    def capture_window(self, handle: int) -> bytes:
        """Capture a window."""


class ClipboardDriver(Protocol):
    def read(self) -> str:
        """Read clipboard text."""

    def write(self, text: str) -> None:
        """Write clipboard text."""

    def clear(self) -> None:
        """Clear clipboard."""


class WindowDriver(Protocol):
    def list(self) -> list[WindowInfo]:
        """List visible windows."""

    def activate(self, title: str) -> None:
        """Activate a window by title."""

    def active(self) -> WindowInfo | None:
        """Return the foreground window."""

    def find(self, title: str) -> list[WindowInfo]:
        """Find windows by title."""

    def close(self, handle: int) -> None:
        """Close a window by handle."""

    def minimize(self, handle: int) -> None:
        """Minimize a window by handle."""

    def restore(self, handle: int) -> None:
        """Restore a window by handle."""

    def rect(self, handle: int) -> Rect:
        """Return window rectangle."""
