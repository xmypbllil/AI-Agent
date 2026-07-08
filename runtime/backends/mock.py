"""Mock backend for the first vertical slice and unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Mapping

from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole


@dataclass(slots=True)
class MockBackend:
    confidence: float = 0.99
    opened_applications: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "mock"

    @property
    def role(self) -> BackendRole:
        return BackendRole.MOCK

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_open_application=True)

    def score(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        if action.kind is not ActionKind.OPEN_APPLICATION:
            return None
        return BackendCandidate(
            backend_name=self.name,
            score=self.confidence,
            reason="supports open application action in mock runtime",
        )

    def execute(self, action: Action) -> ActionResult:
        started = perf_counter()
        if action.kind is not ActionKind.OPEN_APPLICATION:
            return ActionResult(
                action_id=action.action_id,
                status=ActionStatus.FAILED,
                backend_used=self.name,
                backend_score=0.0,
                errors=(f"Unsupported action: {action.kind}",),
            )
        target = str(action.inputs["target"])
        self.opened_applications.append(target)
        return ActionResult(
            action_id=action.action_id,
            status=ActionStatus.SUCCEEDED,
            backend_used=self.name,
            backend_score=self.confidence,
            outputs={"target": target},
            duration_seconds=perf_counter() - started,
        )
