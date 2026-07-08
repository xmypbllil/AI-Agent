"""Null vision adapters."""

from __future__ import annotations

from dataclasses import dataclass

from vision.models import TextMatch


@dataclass(frozen=True, slots=True)
class NullOcrEngine:
    def read_text(self, image: bytes) -> str:
        return ""


@dataclass(frozen=True, slots=True)
class NullTextFinder:
    def find_text(self, image: bytes, text: str) -> list[TextMatch]:
        return []
