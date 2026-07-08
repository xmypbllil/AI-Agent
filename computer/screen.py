"""Screen capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.models import Rect
from computer.ports import ScreenDriver
from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Screen:
    name: str = "screen"
    driver: ScreenDriver | None = None

    def capture(self, region: Rect | None = None) -> bytes:
        return self._driver().capture(region=region)

    def screenshot(self) -> bytes:
        return self.capture()

    def screenshot_region(self, region: Rect) -> bytes:
        return self.capture(region=region)

    def screenshot_window(self, handle: int) -> bytes:
        return self._driver().capture_window(handle)

    def _driver(self) -> ScreenDriver:
        if self.driver is None:
            UnsupportedCapability(self.name)._raise()
        return self.driver
