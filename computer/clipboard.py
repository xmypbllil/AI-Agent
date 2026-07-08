"""Clipboard capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.ports import ClipboardDriver
from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Clipboard:
    name: str = "clipboard"
    driver: ClipboardDriver | None = None

    def read(self) -> str:
        return self._driver().read()

    def get(self) -> str:
        return self.read()

    def write(self, text: str) -> None:
        self._driver().write(text)

    def set(self, text: str) -> None:
        self.write(text)

    def clear(self) -> None:
        self._driver().clear()

    def _driver(self) -> ClipboardDriver:
        if self.driver is None:
            UnsupportedCapability(self.name)._raise()
        return self.driver
