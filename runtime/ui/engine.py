"""UI observation executor."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.backends.manager import BackendManager
from runtime.ui.locator import Locator
from runtime.ui.models import UIElementBounds, UIElementObservation, UITreeSnapshot


@dataclass(slots=True)
class UIObservationExecutor:
    backend_manager: BackendManager

    def find(self, locator: Locator) -> UIElementObservation | None:
        _candidate, backend = self.backend_manager.select_ui_observation_backend(locator)
        return backend.find(locator)

    def find_all(self, locator: Locator) -> tuple[UIElementObservation, ...]:
        _candidate, backend = self.backend_manager.select_ui_observation_backend(locator)
        return backend.find_all(locator)

    def exists(self, locator: Locator) -> bool:
        return self.find(locator) is not None

    def text(self, locator: Locator) -> str | None:
        element = self.find(locator)
        return None if element is None else element.text

    def bounds(self, locator: Locator) -> UIElementBounds | None:
        element = self.find(locator)
        return None if element is None else element.bounds

    def children(self, locator: Locator) -> tuple[UIElementObservation, ...]:
        element = self.find(locator)
        if element is None:
            return ()
        snapshot = self.snapshot_tree(locator)
        return tuple(
            snapshot.elements[child_id]
            for child_id in element.child_ids
            if child_id in snapshot.elements
        )

    def snapshot_tree(self, locator: Locator | None = None) -> UITreeSnapshot:
        selection_locator = locator or Locator()
        _candidate, backend = self.backend_manager.select_ui_observation_backend(selection_locator)
        return backend.snapshot_tree(locator)
