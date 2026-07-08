"""Window management capability contract."""

from __future__ import annotations

from dataclasses import dataclass
import time

from runtime.actions.models import ActionKind, WindowAction
from runtime.actions.engine import ActionExecutor
from runtime.observations import ObservationKind, WindowLocator, WindowObservation, WindowQuery
from runtime.observations.engine import ObservationExecutor


@dataclass(frozen=True, slots=True)
class Windows:
    name: str = "windows"
    action_executor: ActionExecutor | None = None
    observation_executor: ObservationExecutor | None = None

    def list(self) -> list[WindowObservation]:
        result = self._observer().observe(WindowQuery(ObservationKind.WINDOW_LIST))
        return [item for item in result.observations if isinstance(item, WindowObservation)]

    def activate(self, locator: WindowLocator | str) -> None:
        self._executor().execute(WindowAction(ActionKind.ACTIVATE_WINDOW, locator=self._locator(locator)))

    def active(self) -> WindowObservation | None:
        result = self._observer().observe(WindowQuery(ObservationKind.WINDOW_ACTIVE))
        observations = [item for item in result.observations if isinstance(item, WindowObservation)]
        return observations[0] if observations else None

    def find(
        self,
        locator: WindowLocator | str,
        timeout_seconds: float = 0.0,
    ) -> list[WindowObservation]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            result = self._observer().observe(WindowQuery(ObservationKind.WINDOW_FIND, locator=self._locator(locator)))
            matches = [item for item in result.observations if isinstance(item, WindowObservation)]
            if matches or time.monotonic() >= deadline:
                return matches
            time.sleep(0.1)

    def close(self, locator: WindowLocator | str) -> None:
        self._executor().execute(WindowAction(ActionKind.CLOSE_WINDOW, locator=self._locator(locator)))

    def minimize(self, locator: WindowLocator | str) -> None:
        self._executor().execute(WindowAction(ActionKind.MINIMIZE_WINDOW, locator=self._locator(locator)))

    def restore(self, locator: WindowLocator | str) -> None:
        self._executor().execute(WindowAction(ActionKind.RESTORE_WINDOW, locator=self._locator(locator)))

    def bounds(self, locator: WindowLocator | str) -> object | None:
        matches = self.find(locator)
        return matches[0].bounds if matches else None

    def size(self, locator: WindowLocator | str) -> tuple[int, int] | None:
        bounds = self.bounds(locator)
        if bounds is None:
            return None
        return bounds.width, bounds.height

    def _locator(self, locator: WindowLocator | str) -> WindowLocator:
        return WindowLocator(title=locator) if isinstance(locator, str) else locator

    def _executor(self) -> ActionExecutor:
        if self.action_executor is None:
            raise RuntimeError("Window action executor is not configured")
        return self.action_executor

    def _observer(self) -> ObservationExecutor:
        if self.observation_executor is None:
            raise RuntimeError("Window observation executor is not configured")
        return self.observation_executor
