"""UI observation facade."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.ui import Locator, UIElementBounds, UIElementObservation
from runtime.ui.engine import UIObservationExecutor


@dataclass(frozen=True, slots=True)
class UI:
    observation_executor: UIObservationExecutor

    def find(self, locator: Locator) -> UIElementObservation | None:
        return self.observation_executor.find(locator)

    def find_all(self, locator: Locator) -> tuple[UIElementObservation, ...]:
        return self.observation_executor.find_all(locator)

    def exists(self, locator: Locator) -> bool:
        return self.observation_executor.exists(locator)

    def text(self, locator: Locator) -> str | None:
        return self.observation_executor.text(locator)

    def bounds(self, locator: Locator) -> UIElementBounds | None:
        return self.observation_executor.bounds(locator)

    def children(self, locator: Locator) -> tuple[UIElementObservation, ...]:
        return self.observation_executor.children(locator)
