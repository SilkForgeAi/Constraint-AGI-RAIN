"""Zero-copy context sharing: write thought process to shared memory for ADOM/observer.

When RAIN_SHARED_CONTEXT_PATH is set, Rain writes a minimal state (turn_id, prompt_preview,
response_preview, memory_preview) to a memory-mapped file or regular file so an external
process (e.g. ADOM) can read without REST/JSON latency. Enables "thinking at the speed of CPU."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Max bytes to write (keeps shared block small)
MAX_SHARED_BYTES = 65536  # 64KB


class SharedContext:
    """Write current thought context to a shared path for zero-copy reads by observer."""

    def __init__(self, path: str | Path | None = None):
        self._path: Path | None = Path(path).resolve() if path else None
        self._turn_id = 0

    def write(
        self,
        prompt_preview: str = "",
        response_preview: str = "",
        memory_preview: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Write current context to shared path. Truncates to fit MAX_SHARED_BYTES."""
        if not self._path:
            return
        self._turn_id += 1
        payload = {
            "turn_id": self._turn_id,
            "prompt_preview": (prompt_preview or "")[:2000],
            "response_preview": (response_preview or "")[:2000],
            "memory_preview": (memory_preview or "")[:2000],
            **(extra or {}),
        }
        raw = json.dumps(payload, ensure_ascii=False)
        if len(raw.encode("utf-8")) > MAX_SHARED_BYTES - 2:
            raw = raw[: (MAX_SHARED_BYTES // 4)] + "...[truncated]"
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(raw, encoding="utf-8")
        except Exception:
            pass

    def clear(self) -> None:
        """Clear shared context (e.g. on shutdown)."""
        if not self._path:
            return
        try:
            if self._path.exists():
                self._path.write_text("{}", encoding="utf-8")
        except Exception:
            pass


def get_shared_context(path: str | None = None):
    """Return SharedContext if RAIN_SHARED_CONTEXT_PATH is set, else a no-op instance."""
    from rain.config import SHARED_CONTEXT_PATH
    p = path or SHARED_CONTEXT_PATH
    return SharedContext(p) if p else SharedContext(None)
