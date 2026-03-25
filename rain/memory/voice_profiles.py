"""Voice profile storage: enroll speakers by name, identify by embedding. L2 nearest-neighbor."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from rain.voice.schema import VoiceProfile


def _l2(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return float("inf")
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class VoiceProfileStore:
    """SQLite-backed store for voice profiles (name, embedding). Identify by L2 nearest neighbor."""

    def __init__(self, db_path: Path):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS voice_profiles (
                    voice_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    created_at TEXT
                )"""
            )

    def add(self, profile: VoiceProfile) -> None:
        """Store a voice profile."""
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO voice_profiles (voice_id, name, embedding_json, created_at) VALUES (?, ?, ?, ?)",
                (profile.voice_id, profile.name, json.dumps(profile.embedding), profile.created_at or ""),
            )

    def list_all(self) -> list[VoiceProfile]:
        """Return all stored profiles."""
        out = []
        with sqlite3.connect(self._path) as conn:
            for row in conn.execute("SELECT voice_id, name, embedding_json, created_at FROM voice_profiles"):
                emb = json.loads(row[2])
                out.append(VoiceProfile(name=row[1], voice_id=row[0], embedding=emb, created_at=row[3] or ""))
        return out

    def identify(self, embedding: list[float], threshold: float = 0.5) -> str | None:
        """Return name of nearest profile if L2 distance <= threshold, else None."""
        profiles = self.list_all()
        if not profiles or not embedding:
            return None
        best_name: str | None = None
        best_dist = float("inf")
        for p in profiles:
            d = _l2(embedding, p.embedding)
            if d < best_dist and d <= threshold:
                best_dist = d
                best_name = p.name
        return best_name

    def get_by_name(self, name: str) -> VoiceProfile | None:
        """Return first profile with this name."""
        for p in self.list_all():
            if p.name == name:
                return p
        return None

    def delete(self, voice_id: str) -> bool:
        """Remove a profile by voice_id. Returns True if deleted."""
        with sqlite3.connect(self._path) as conn:
            cur = conn.execute("DELETE FROM voice_profiles WHERE voice_id = ?", (voice_id,))
            return cur.rowcount > 0
