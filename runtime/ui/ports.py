"""UI backend protocols."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from runtime.actions.models import Action, ActionResult
from runtime.backends.models import BackendCapabilities, BackendCandidate, BackendRole
from runtime.ui.locator import Locator
from runtime.ui.models import UIElementObservation, UITreeSnapshot


class UIObservationBackend(Protocol):
    @property
    def name(self) -> str:
        """Stable backend name."""

    @property
    def role(self) -> BackendRole:
        """Backend role in the fallback chain."""

    @property
    def capabilities(self) -> BackendCapabilities:
        """Declared backend capabilities."""

    def score_locator(
        self,
        locator: Locator,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        """Score this backend for a locator query."""

    def find(self, locator: Locator) -> UIElementObservation | None:
        """Find one UI element without mutating desktop state."""

    def find_all(self, locator: Locator) -> tuple[UIElementObservation, ...]:
        """Find all matching UI elements without mutating desktop state."""

    def snapshot_tree(self, locator: Locator | None = None) -> UITreeSnapshot:
        """Read a UI tree snapshot."""


class UIActionBackend(Protocol):
    @property
    def name(self) -> str:
        """Stable backend name."""

    @property
    def role(self) -> BackendRole:
        """Backend role in the fallback chain."""

    @property
    def capabilities(self) -> BackendCapabilities:
        """Declared backend capabilities."""

    def score_ui_action(
        self,
        action: Action,
        context: Mapping[str, Any] | None = None,
    ) -> BackendCandidate | None:
        """Score this backend for a UI action."""

    def execute_ui(self, action: Action) -> ActionResult:
        """Execute a UI action that mutates desktop state."""
