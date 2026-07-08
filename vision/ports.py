"""Vision protocols."""

from __future__ import annotations

from typing import Protocol

from vision.models import TextMatch


class OcrEngine(Protocol):
    def read_text(self, image: bytes) -> str:
        """Extract text from an image."""


class TextFinder(Protocol):
    def find_text(self, image: bytes, text: str) -> list[TextMatch]:
        """Find text instances in an image."""
