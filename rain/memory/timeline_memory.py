"""Timeline memory — chronological events and episodes."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class TimelineMemory:
    """Stores events in chronological order."""

    def __init__(self, db_path: Path):
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")

    def add(self, event_type: str, content: str, metadata: dict | None = None) -> int:
        """Append an event. Returns event id."""
        meta_str = json.dumps(metadata or {})
        with sqlite3.connect(self._path) as conn:
            cur = conn.execute(
                "INSERT INTO events (event_type, content, metadata) VALUES (?, ?, ?)",
                (event_type, content, meta_str),
            )
            return cur.lastrowid or 0

    def recent(self, limit: int = 20, event_type: str | None = None) -> list[dict]:
        """Get most recent events."""
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                    (event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except json.JSONDecodeError:
                        pass
                out.append(d)
            return out

    def delete(self, event_id: int) -> bool:
        """Delete an event by id. Returns True if deleted."""
        with sqlite3.connect(self._path) as conn:
            cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return cur.rowcount > 0

    def range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get events in a time range."""
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM events WHERE 1=1"
            params: list = []
            if start:
                q += " AND timestamp >= ?"
                params.append(start.isoformat())
            if end:
                q += " AND timestamp <= ?"
                params.append(end.isoformat())
            q += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]
