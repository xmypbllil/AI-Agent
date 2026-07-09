# merged.md

"""Action executor."""

from __future__ import annotations

from dataclasses import dataclass, field

---

"""World model cache.

The world model is a cache, not the source of truth. Callers can mark it stale and refresh from
observation backends.
"""
