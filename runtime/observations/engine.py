"""Observation executor."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.backends.manager import BackendManager
from runtime.observations.queries import ObservationQuery, ObservationResult
from runtime.world import WorldModel


@dataclass(slots=True)
class ObservationExecutor:
    backend_manager: BackendManager
    world: WorldModel | None = None

    def observe(self, query: ObservationQuery) -> ObservationResult:
        candidate, backend = self.backend_manager.select_observation_backend(query)
        result = backend.observe(query)
        result = ObservationResult(
            query_id=result.query_id,
            backend_used=result.backend_used or candidate.backend_name,
            backend_score=result.backend_score or candidate.score,
            backend_reason=result.backend_reason or candidate.reason,
            observations=result.observations,
            errors=result.errors,
        )
        if self.world is not None and result.observations:
            self.world.apply_many(result.observations)
        return result
