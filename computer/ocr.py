"""OCR bridge capability."""

from __future__ import annotations

from dataclasses import dataclass

from computer.unsupported import UnsupportedCapability


@dataclass(frozen=True, slots=True)
class Ocr(UnsupportedCapability):
    name: str = "ocr"

    def read_text(self, image: bytes) -> str:
        self._raise()
