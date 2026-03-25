"""
Latency instrumentation for Rain — time-to-first-token and time-to-complete.
Enables latency budgets, percentiles (p50, p95), and speed-of-thinking optimization.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

_MAX_SAMPLES = 2000
_samples: dict[str, deque[dict[str, Any]]] = {}
_lock = threading.Lock()


def record(
    phase: str,
    time_to_first_token_ms: float | None = None,
    time_to_complete_ms: float | None = None,
    provider: str = "",
    model: str = "",
) -> None:
    """Record one LLM call. phase e.g. complete, complete_stream, think."""
    with _lock:
        if phase not in _samples:
            _samples[phase] = deque(maxlen=_MAX_SAMPLES)
        entry = {
            "ttft_ms": time_to_first_token_ms,
            "ttc_ms": time_to_complete_ms,
            "provider": provider or "",
            "model": model or "",
            "ts": time.time(),
        }
        _samples[phase].append(entry)


def get_recent(phase: str = "complete", n: int = 100) -> list[dict[str, Any]]:
    """Last n samples for a phase."""
    with _lock:
        d = _samples.get(phase, deque())
        return list(d)[-n:]


def get_percentiles(phase: str = "complete", p50: bool = True, p95: bool = True) -> dict[str, float | None]:
    """Compute p50 and p95 for time_to_complete_ms and ttft for phase."""
    with _lock:
        d = _samples.get(phase, deque())
        if not d:
            return {"p50_ttc_ms": None, "p95_ttc_ms": None, "p50_ttft_ms": None, "p95_ttft_ms": None}
        ttc = [e["ttc_ms"] for e in d if e.get("ttc_ms") is not None]
        ttft = [e["ttft_ms"] for e in d if e.get("ttft_ms") is not None]
        ttc.sort()
        ttft.sort()
        out = {}
        out["p50_ttc_ms"] = ttc[int(len(ttc) * 0.50)] if ttc else None
        out["p95_ttc_ms"] = ttc[int(len(ttc) * 0.95)] if ttc else None
        out["p50_ttft_ms"] = ttft[int(len(ttft) * 0.50)] if ttft else None
        out["p95_ttft_ms"] = ttft[int(len(ttft) * 0.95)] if ttft else None
        return out


def clear(phase: str | None = None) -> None:
    """Clear samples. For tests."""
    with _lock:
        if phase is None:
            _samples.clear()
        elif phase in _samples:
            _samples[phase].clear()
