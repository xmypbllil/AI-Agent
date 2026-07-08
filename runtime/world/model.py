"""World model cache.

The world model is a cache, not the source of truth. Callers can mark it stale and refresh from
observation backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from runtime.observations.models import ProcessObservation, WindowObservation


@dataclass(frozen=True, slots=True)
class WorldSnapshot:
    data: Mapping[str, Any]
    captured_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass(slots=True)
class WorldModel:
    snapshot: WorldSnapshot = field(default_factory=lambda: WorldSnapshot(data={}))
    stale: bool = True

    def update(self, data: Mapping[str, Any]) -> WorldSnapshot:
        self.snapshot = WorldSnapshot(data=dict(data))
        self.stale = False
        return self.snapshot

    def mark_stale(self) -> None:
        self.stale = True

    def apply_observations(self, observations: Mapping[str, Any]) -> WorldSnapshot:
        data = dict(self.snapshot.data)
        processes = list(data.get("processes", ()))
        windows = list(data.get("windows", ()))

        process = observations.get("process")
        if isinstance(process, ProcessObservation):
            processes = [item for item in processes if item.identity.pid != process.identity.pid]
            processes.append(process)
            data["processes"] = tuple(processes)

        window = observations.get("window")
        if isinstance(window, WindowObservation):
            windows = [
                item
                for item in windows
                if not (
                    item.identity.title == window.identity.title
                    and item.identity.process_id == window.identity.process_id
                )
            ]
            windows.append(window)
            data["windows"] = tuple(windows)
            if window.active:
                data["active_window"] = window.identity

        return self.update(data)

    def apply_many(self, observations: tuple[Any, ...]) -> WorldSnapshot:
        snapshot = self.snapshot
        for observation in observations:
            if isinstance(observation, ProcessObservation):
                snapshot = self.apply_observations({"process": observation})
            elif isinstance(observation, WindowObservation):
                snapshot = self.apply_observations({"window": observation})
        return snapshot
