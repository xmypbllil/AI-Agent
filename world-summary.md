# world-summary.md

"""World model cache.

The world model is a cache, not the source of truth. Callers can mark it stale and refresh from
observation backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
