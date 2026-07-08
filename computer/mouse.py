"""Mouse capability contract."""

from __future__ import annotations

from dataclasses import dataclass

from computer.models import MouseButton, Point
from computer.ports import MouseDriver
from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Mouse:
    name: str = "mouse"
    driver: MouseDriver | None = None

    def move(self, point: Point) -> None:
        self._driver().move(point)

    def click(self, point: Point | None = None, button: MouseButton = MouseButton.LEFT) -> None:
        self._driver().click(point=point, button=button)

    def drag(self, start: Point, end: Point, button: MouseButton = MouseButton.LEFT) -> None:
        self._driver().drag(start=start, end=end, button=button)

    def scroll(self, amount: int, point: Point | None = None) -> None:
        self._driver().scroll(amount=amount, point=point)

    def _driver(self) -> MouseDriver:
        if self.driver is None:
            UnsupportedCapability(self.name)._raise()
        return self.driver
