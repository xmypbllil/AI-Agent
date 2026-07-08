"""Backend protocols."""

from __future__ import annotations

from typing import Protocol

from typing import Any, Mapping

from runtime.actions.models import Action, ActionResult
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.observations import ObservationQuery, ObservationResult


class ActionBackend(Protocol):
    @property
    def name(self) -> str:
        """Stable backend name."""

    @property
    def role(self) -> BackendRole:
        """Backend role in the fallback chain."""

    @property
    def capabilities(self) -> BackendCapabilities:
        """Declared backend capabilities."""

    def score(self, action: Action, context: Mapping[str, Any] | None = None) -> BackendCandidate | None:
        """Return backend confidence for an action, or None if unsupported."""

    def execute(self, action: Action) -> ActionResult:
        """Execute an action."""


class ObservationBackend(Protocol):
    @property
    def name(self) -> str:
        """Stable backend name."""

    @property
    def role(self) -> BackendRole:
        """Backend role in the fallback chain."""

    @property
    def capabilities(self) -> BackendCapabilities:
        """Declared backend capabilities."""

    def score_observation(
        self,
        query: ObservationQuery,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        """Return backend confidence for an observation query."""

    def observe(self, query: ObservationQuery) -> ObservationResult:
        """Read state without changing it."""
