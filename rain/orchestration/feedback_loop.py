"""Turn-level feedback log for offline review and optional lesson mining.

No weight updates — append-only JSONL for human / batch processes.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


class TurnFeedbackLog:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.RLock()

    def record(
        self,
        *,
        prompt_preview: str,
        response_preview: str,
        use_tools: bool,
        use_memory: bool,
        gi_mode: str | None,
        explore: bool,
        outcome: str = "ok",
        extra: dict[str, Any] | None = None,
    ) -> None:
        rec = {
            "ts": time.time(),
            "prompt_preview": (prompt_preview or "")[:500],
            "response_preview": (response_preview or "")[:800],
            "use_tools": use_tools,
            "use_memory": use_memory,
            "gi_mode": gi_mode,
            "explore": explore,
            "outcome": outcome,
            "extra": extra or {},
        }
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line)
