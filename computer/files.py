"""Filesystem capability."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Files:
    root: Path | None = None

    def _resolve(self, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute() and self.root is not None:
            candidate = self.root / candidate
        resolved = candidate.resolve()
        if self.root is not None and not resolved.is_relative_to(self.root.resolve()):
            raise PermissionError(f"Path escapes configured root: {resolved}")
        return resolved

    def read(self, path: str | Path, encoding: str = "utf-8") -> str:
        return self._resolve(path).read_text(encoding=encoding)

    def write(self, path: str | Path, content: str, encoding: str = "utf-8") -> None:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)

    def exists(self, path: str | Path) -> bool:
        return self._resolve(path).exists()

    def list(self, path: str | Path = ".") -> list[str]:
        return [item.name for item in self._resolve(path).iterdir()]
