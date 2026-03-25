"""Structured subject–predicate–object facts (lightweight KR boundary).

Stored as JSONL under DATA_DIR. Used for prompt injection and explicit recall.
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any


class StructuredFactStore:
    """Append-only fact log with simple query overlap for prompt injection."""

    def __init__(self, path: Path, max_file_bytes: int = 2_000_000):
        self._path = path
        self._max_file_bytes = max_file_bytes
        self._lock = threading.RLock()

    def _ensure(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def add_fact(self, subject: str, predicate: str, obj: str, source: str = "session") -> None:
        s, p, o = (subject or "").strip(), (predicate or "").strip(), (obj or "").strip()
        if not s or not p:
            return
        rec = {
            "subject": s[:500],
            "predicate": p[:500],
            "object": o[:2000],
            "source": (source or "session")[:64],
            "ts": time.time(),
        }
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        with self._lock:
            self._ensure()
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line)
            self._maybe_trim_unlocked()

    def _maybe_trim_unlocked(self) -> None:
        try:
            if self._path.stat().st_size <= self._max_file_bytes:
                return
            # Keep tail ~half the file by re-reading last N lines (simple)
            raw = self._path.read_text(encoding="utf-8", errors="replace")
            lines = raw.splitlines()
            keep = lines[-8000:] if len(lines) > 8000 else lines
            self._path.write_text("\n".join(keep) + "\n", encoding="utf-8")
        except Exception:
            pass

    def facts_for_prompt(self, query: str, limit: int = 10) -> str:
        q = (query or "").strip().lower()
        if not q:
            return ""
        words = set(re.findall(r"[a-z0-9]{3,}", q))
        if not words:
            return ""
        rows: list[tuple[float, str]] = []
        with self._lock:
            self._ensure()
            try:
                text = self._path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""
        for line in text.splitlines()[-12000:]:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            blob = f"{rec.get('subject', '')} {rec.get('predicate', '')} {rec.get('object', '')}".lower()
            score = sum(1 for w in words if w in blob)
            if score > 0:
                rows.append((float(score), rec))
        rows.sort(key=lambda x: -x[0])
        out_lines: list[str] = []
        for _sc, rec in rows[: max(1, limit)]:
            out_lines.append(
                f"- ({rec.get('subject', '')}) —[{rec.get('predicate', '')}]→ ({rec.get('object', '')})"
            )
        if not out_lines:
            return ""
        return "[Structured facts — verified claims only; treat as user/session assertions]\n" + "\n".join(out_lines)


def get_fact_store(data_dir: Path) -> StructuredFactStore:
    return StructuredFactStore(data_dir / "knowledge_facts.jsonl")
