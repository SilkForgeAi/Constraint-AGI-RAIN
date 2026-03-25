"""Session store: file management, SQLite index, retention, legal hold."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _sanitize_speaker(s: str) -> str:
    """Safe for filenames."""
    return re.sub(r"[^\w\-]", "_", (s or "unknown")[:64])


class SessionStore:
    """SQLite index of all sessions; retention purge; legal hold."""

    def __init__(self, db_path: Path, sessions_dir: Path):
        self._db_path = Path(db_path)
        self._sessions_dir = Path(sessions_dir)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    speaker_name TEXT,
                    speaker_id TEXT,
                    wav_path TEXT,
                    json_path TEXT,
                    file_hash TEXT,
                    duration_seconds REAL,
                    legal_hold INTEGER DEFAULT 0,
                    created_at TEXT
                )"""
            )

    def add_session(
        self,
        session_id: str,
        start_time: str,
        end_time: str,
        speaker_name: str | None = None,
        speaker_id: str | None = None,
        wav_path: str | None = None,
        json_path: str | None = None,
        file_hash: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO sessions (
                    session_id, start_time, end_time, speaker_name, speaker_id,
                    wav_path, json_path, file_hash, duration_seconds, legal_hold, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (
                    session_id,
                    start_time,
                    end_time,
                    speaker_name or "",
                    speaker_id or "",
                    wav_path or "",
                    json_path or "",
                    file_hash or "",
                    duration_seconds or 0.0,
                    now,
                ),
            )

    def list_sessions(self, limit: int = 200) -> list[dict[str, Any]]:
        """List sessions newest first."""
        out = []
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(
                "SELECT session_id, start_time, end_time, speaker_name, speaker_id, wav_path, json_path, file_hash, duration_seconds, legal_hold, created_at FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ):
                out.append(dict(row))
        return out

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT session_id, start_time, end_time, speaker_name, speaker_id, wav_path, json_path, file_hash, duration_seconds, legal_hold, created_at FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def set_legal_hold(self, session_id: str, hold: bool) -> bool:
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute("UPDATE sessions SET legal_hold = ? WHERE session_id = ?", (1 if hold else 0, session_id))
            return cur.rowcount > 0

    def purge_retention(self, retention_days: int) -> int:
        """Delete sessions older than retention_days that are not under legal_hold. Returns count purged."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        purged = 0
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT session_id, wav_path, json_path FROM sessions WHERE created_at < ? AND (legal_hold IS NULL OR legal_hold = 0)",
                (cutoff,),
            ).fetchall()
            for row in rows:
                sid, wav, jpath = row[0], row[1], row[2]
                for p in (wav, jpath):
                    if p:
                        try:
                            Path(p).unlink(missing_ok=True)
                        except Exception:
                            pass
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
                purged += 1
        return purged

    def session_file_paths(self, session_id: str, timestamp: str, speaker: str) -> tuple[Path, Path]:
        """Return (wav_path, json_path) for a new session."""
        safe_speaker = _sanitize_speaker(speaker)
        base = self._sessions_dir / f"{session_id}_{timestamp}_{safe_speaker}"
        return base.with_suffix(".wav"), base.with_suffix(".json")
