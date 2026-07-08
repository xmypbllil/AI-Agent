"""SQLite memory store."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from memory.models import CacheEntry, MemoryEvent


@dataclass(slots=True)
class SQLiteMemory:
    path: Path

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            connection.commit()

    def append_event(self, event: MemoryEvent) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO events(kind, payload, created_at) VALUES (?, ?, ?)",
                (event.kind, event.payload, event.created_at.isoformat()),
            )
            connection.commit()

    def recent_events(self, limit: int = 50) -> list[MemoryEvent]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT kind, payload, created_at FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [MemoryEvent(kind=row[0], payload=row[1]) for row in rows]

    def put_cache(self, entry: CacheEntry) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO cache(key, value, created_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, created_at=excluded.created_at
                """,
                (entry.key, entry.value, entry.created_at.isoformat()),
            )
            connection.commit()

    def get_cache(self, key: str) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)
