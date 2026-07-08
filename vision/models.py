"""Vision models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextMatch:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int
