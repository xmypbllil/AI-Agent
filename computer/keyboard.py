"""Keyboard capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.ports import KeyboardDriver
from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Keyboard:
    name: str = "keyboard"
    driver: KeyboardDriver | None = None

    def write(self, text: str) -> None:
        self._driver().write(text)

    def press(self, key: str) -> None:
        self._driver().press(key)

    def hotkey(self, *keys: str) -> None:
        self._driver().hotkey(*keys)

    def hold(self, key: str) -> None:
        self._driver().hold(key)

    def release(self, key: str) -> None:
        self._driver().release(key)

    def _driver(self) -> KeyboardDriver:
        if self.driver is None:
            UnsupportedCapability(self.name)._raise()
        return self.driver
