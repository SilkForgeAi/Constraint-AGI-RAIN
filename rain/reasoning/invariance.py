"""
Invariance cache — same logical question -> same answer (prompt invariance).
Perfect reasoner fix: rephrasing the question doesn't change the conclusion.
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore

CACHE_PREFIX = "invariance_"
CACHE_KIND = "invariance"
MIN_CONFIDENCE_TO_RETURN = 0.8


def normalize_question(prompt: str, context_prefix: str = "") -> str:
    """Canonical form: lowercase, collapse whitespace, remove leading/trailing."""
    s = (context_prefix + " " + (prompt or "")).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s[:500]


def _key(normalized: str) -> str:
    h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{CACHE_PREFIX}{h}"


def get_cached_answer(memory: "MemoryStore", normalized: str) -> tuple[str, float] | None:
    """Return (answer, confidence) if we have a cache hit, else None."""
    try:
        raw = memory.symbolic.get(_key(normalized), CACHE_KIND)
        if raw and isinstance(raw, dict):
            ans = raw.get("answer")
            conf = float(raw.get("confidence", 0))
            if ans is not None and conf >= MIN_CONFIDENCE_TO_RETURN:
                return (str(ans)[:8000], conf)
    except Exception:
        pass
    return None


def set_cached_answer(
    memory: "MemoryStore",
    normalized: str,
    answer: str,
    confidence: float,
) -> None:
    """Store answer in cache for this canonical question."""
    try:
        from datetime import datetime
        memory.remember_fact(
            _key(normalized),
            {
                "answer": (answer or "")[:8000],
                "confidence": round(confidence, 3),
                "updated_at": datetime.utcnow().isoformat(),
            },
            kind=CACHE_KIND,
        )
    except Exception:
        pass
