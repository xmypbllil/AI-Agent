"""Shared computer API models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MouseButton(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class WindowState(StrEnum):
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Rect:
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    pid: int
    name: str
    executable: str | None = None
    window_title: str | None = None


@dataclass(frozen=True, slots=True)
class WindowInfo:
    handle: int
    title: str
    rect: Rect | None = None
    process_id: int | None = None
    class_name: str | None = None
    state: WindowState = WindowState.NORMAL
