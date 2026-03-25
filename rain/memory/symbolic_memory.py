"""Symbolic memory — structured facts and knowledge."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from rain.memory.sqlite_recovery import init_sqlite_or_rename_corrupt


class SymbolicMemory:
    """Stores facts as key-value / graph-like structure."""

    def __init__(self, db_path: Path):
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        def _setup(conn: sqlite3.Connection) -> None:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT,
                    kind TEXT DEFAULT 'fact',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(key, kind)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_facts_kind ON facts(kind)
            """)

        init_sqlite_or_rename_corrupt(self._path, _setup)

    def set(self, key: str, value: Any, kind: str = "fact") -> None:
        """Store or update a fact."""
        val_str = json.dumps(value) if not isinstance(value, str) else value
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO facts (key, value, kind) VALUES (?, ?, ?)
                ON CONFLICT(key, kind) DO UPDATE SET value = excluded.value
                """,
                (key, val_str, kind),
            )

    def get(self, key: str, kind: str | None = None) -> Any | None:
        """Retrieve a fact by key."""
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            if kind:
                row = conn.execute(
                    "SELECT value FROM facts WHERE key = ? AND kind = ?",
                    (key, kind),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT value FROM facts WHERE key = ? ORDER BY created_at DESC LIMIT 1",
                    (key,),
                ).fetchone()
            if row:
                val = row["value"]
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return val
            return None

    def get_all(self, kind: str | None = None) -> list[dict]:
        """Get all facts, optionally filtered by kind."""
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            if kind:
                rows = conn.execute("SELECT * FROM facts WHERE kind = ?", (kind,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM facts").fetchall()
            return [dict(r) for r in rows]

    def delete(self, key: str, kind: str | None = None) -> bool:
        """Remove a fact."""
        with sqlite3.connect(self._path) as conn:
            if kind:
                cur = conn.execute("DELETE FROM facts WHERE key = ? AND kind = ?", (key, kind))
            else:
                cur = conn.execute("DELETE FROM facts WHERE key = ?", (key,))
            return cur.rowcount > 0
