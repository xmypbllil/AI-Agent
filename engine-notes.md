# engine-notes.md

"""Action executor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter, sleep

from runtime.actions.models import Action, ActionKind, ActionResult, ActionStatus
from runtime.backends.manager import BackendManager
