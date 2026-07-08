"""Action executor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter, sleep

from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.manager import BackendManager
from runtime.world import WorldModel


@dataclass(slots=True)
class ActionExecutor:
    backend_manager: BackendManager
    world: WorldModel | None = None
    history: list[ActionResult] = field(default_factory=list)

    def execute(self, action: Action) -> ActionResult:
        attempts = max(1, action.retry_policy.max_attempts)
        last_result: ActionResult | None = None
        for attempt in range(attempts):
            started = perf_counter()
            started_at = datetime.now(tz=UTC)
            if action.kind in {ActionKind.CLICK, ActionKind.TYPE_TEXT}:
                candidate, backend = self.backend_manager.select_ui_action_backend(action)
                result = backend.execute_ui(action)
            else:
                candidate, backend = self.backend_manager.select_action_backend(action)
                result = backend.execute(action)
            result = ActionResult(
                action_id=result.action_id,
                status=result.status,
                started_at=result.started_at or started_at,
                finished_at=result.finished_at or datetime.now(tz=UTC),
                duration_seconds=result.duration_seconds or perf_counter() - started,
                backend_used=result.backend_used or candidate.backend_name,
                backend_score=result.backend_score or candidate.score,
                backend_reason=result.backend_reason or candidate.reason,
                outputs=result.outputs,
                errors=result.errors,
                observations=result.observations,
                screenshots=result.screenshots,
                telemetry={**result.telemetry, "attempt": attempt + 1},
            )
            self.history.append(result)
            if self.world is not None and result.observations:
                self.world.apply_observations(result.observations)
            last_result = result
            if result.status is ActionStatus.SUCCEEDED:
                return result
            if action.retry_policy.delay_seconds > 0 and attempt + 1 < attempts:
                sleep(action.retry_policy.delay_seconds)
        if last_result is None:
            raise RuntimeError("Action execution produced no result")
        return last_result
