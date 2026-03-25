"""
Session world model: compact, updatable state per session (key facts, last exchange summaries).
Feeds a short summary into the next prompt so Rain is not stateless.
SAFETY: In-memory only. No execution. No persistence across process restarts unless caller saves/loads.
"""

from __future__ import annotations

from collections import deque
from typing import Deque


class SessionWorldModel:
    """Bounded session state: recent turn summaries for context."""

    def __init__(self, max_entries: int = 20, max_chars_per_entry: int = 200):
        self._entries: Deque[str] = deque(maxlen=max_entries)
        self._max_chars_per_entry = max_chars_per_entry

    def update(self, turn_summary: str) -> None:
        """Append a short summary of the last turn (e.g. user said X; Rain said Y)."""
        s = (turn_summary or "").strip()
        if s:
            self._entries.append(s[: self._max_chars_per_entry])

    def get_context(self, max_chars: int = 800) -> str:
        """Return a string to inject into the prompt (recent session state)."""
        if not self._entries:
            return ""
        lines = list(self._entries)
        out: list[str] = []
        n = 0
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if n + len(line) + 2 > max_chars:
                break
            out.append(line)
            n += len(line) + 2
        out.reverse()
        return ("Session (recent):\n" + "\n".join(out)) if out else ""
