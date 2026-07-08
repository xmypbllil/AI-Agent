"""Backend manager with capability scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from runtime.actions.models import Action
from runtime.observations import ObservationQuery
from runtime.backends.models import BackendCandidate
from runtime.backends.ports import ActionBackend, ObservationBackend
from runtime.errors import BackendUnavailableError
from runtime.ui.locator import Locator
from runtime.ui.ports import UIActionBackend, UIObservationBackend


@dataclass(slots=True)
class BackendManager:
    action_backends: list[ActionBackend] = field(default_factory=list)
    observation_backends: list[ObservationBackend] = field(default_factory=list)
    ui_observation_backends: list[UIObservationBackend] = field(default_factory=list)
    ui_action_backends: list[UIActionBackend] = field(default_factory=list)

    def register_action_backend(self, backend: ActionBackend) -> None:
        self.action_backends.append(backend)

    def register_observation_backend(self, backend: ObservationBackend) -> None:
        self.observation_backends.append(backend)

    def register_ui_observation_backend(self, backend: UIObservationBackend) -> None:
        self.ui_observation_backends.append(backend)

    def register_ui_action_backend(self, backend: UIActionBackend) -> None:
        self.ui_action_backends.append(backend)

    def candidates(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> list[tuple[BackendCandidate, ActionBackend]]:
        scored = [
            (candidate, backend)
            for backend in self.action_backends
            if (candidate := backend.score(action, context=context)) is not None
        ]
        scored.sort(key=lambda item: item[0].score, reverse=True)
        return scored

    def select_action_backend(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[BackendCandidate, ActionBackend]:
        scored = self.candidates(action, context=context)
        if not scored:
            raise BackendUnavailableError(f"No backend can execute action: {action.kind}")
        return scored[0]

    def observation_candidates(
        self,
        query: ObservationQuery,
        context: Mapping[str, Any] | None = None,
    ) -> list[tuple[BackendCandidate, ObservationBackend]]:
        scored = [
            (candidate, backend)
            for backend in self.observation_backends
            if (candidate := backend.score_observation(query, context=context)) is not None
        ]
        scored.sort(key=lambda item: item[0].score, reverse=True)
        return scored

    def select_observation_backend(
        self,
        query: ObservationQuery,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[BackendCandidate, ObservationBackend]:
        scored = self.observation_candidates(query, context=context)
        if not scored:
            raise BackendUnavailableError(f"No backend can observe query: {query.kind}")
        return scored[0]

    def ui_observation_candidates(
        self,
        locator: Locator,
        context: Mapping[str, Any] | None = None,
    ) -> list[tuple[BackendCandidate, UIObservationBackend]]:
        scored = [
            (candidate, backend)
            for backend in self.ui_observation_backends
            if (candidate := backend.score_locator(locator, context=context)) is not None
        ]
        scored.sort(key=lambda item: item[0].score, reverse=True)
        return scored

    def select_ui_observation_backend(
        self,
        locator: Locator,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[BackendCandidate, UIObservationBackend]:
        scored = self.ui_observation_candidates(locator, context=context)
        if not scored:
            raise BackendUnavailableError("No backend can observe UI locator")
        return scored[0]

    def ui_action_candidates(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> list[tuple[BackendCandidate, UIActionBackend]]:
        scored = [
            (candidate, backend)
            for backend in self.ui_action_backends
            if (candidate := backend.score_ui_action(action, context=context)) is not None
        ]
        scored.sort(key=lambda item: item[0].score, reverse=True)
        return scored

    def select_ui_action_backend(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[BackendCandidate, UIActionBackend]:
        scored = self.ui_action_candidates(action, context=context)
        if not scored:
            raise BackendUnavailableError(f"No backend can execute UI action: {action.kind}")
        return scored[0]
