"""
Lightweight belief state — proposition -> confidence with simple evidence-based update.
Perfect reasoner pillar: formal epistemology (approximate). Enables calibrated uncertainty.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore

BELIEF_PREFIX = "belief_"
MAX_BELIEFS_FOR_CONTEXT = 5
CONFIDENCE_DECAY = 0.95  # slight decay over time so old beliefs don't dominate


def _key(proposition: str) -> str:
    p = (proposition or "").strip()[:200]
    h = hashlib.sha256(p.encode()).hexdigest()[:14]
    return f"{BELIEF_PREFIX}{h}"


def update(
    memory: "MemoryStore",
    proposition: str,
    evidence_strength: float,
    supported: bool,
    namespace: str | None = None,
) -> float:
    """
    Lightweight Bayesian-like update: prior + evidence -> posterior.
    supported=True: posterior = min(1, prior + evidence_strength * (1 - prior))
    supported=False: posterior = max(0, prior - evidence_strength * prior)
    Returns new confidence in [0, 1].
    """
    proposition = (proposition or "").strip()[:200]
    if not proposition:
        return 0.5
    strength = max(0.0, min(1.0, evidence_strength))
    key = _key(proposition)
    try:
        raw = memory.symbolic.get(key, "belief")
        if raw and isinstance(raw, dict):
            prior = float(raw.get("confidence", 0.5))
        else:
            prior = 0.5
    except Exception:
        prior = 0.5
    if supported:
        posterior = min(1.0, prior + strength * (1.0 - prior))
    else:
        posterior = max(0.0, prior - strength * prior)
    from datetime import datetime
    memory.remember_fact(key, {
        "proposition": proposition,
        "confidence": round(posterior, 4),
        "updated_at": datetime.utcnow().isoformat(),
        "namespace": namespace or "chat",
    }, kind="belief")
    return posterior


def get(memory: "MemoryStore", proposition: str) -> float | None:
    """Return confidence for proposition, or None if not stored."""
    key = _key((proposition or "").strip()[:200])
    try:
        raw = memory.symbolic.get(key, "belief")
        if raw and isinstance(raw, dict):
            return float(raw.get("confidence", 0.5))
    except Exception:
        pass
    return None


def get_uncertainty_context(memory: "MemoryStore", top_k: int = MAX_BELIEFS_FOR_CONTEXT) -> str:
    """Return a short string of low-confidence beliefs for prompt context (what Rain is uncertain about)."""
    try:
        import json
        rows = memory.symbolic.get_all("belief")
        if not rows:
            return ""
        items = []
        for row in rows:
            val = row.get("value")
            if isinstance(val, str):
                try:
                    v = json.loads(val)
                except Exception:
                    continue
            else:
                v = val if isinstance(val, dict) else None
            if not v:
                continue
            conf = float(v.get("confidence", 0.5))
            if conf < 0.7:
                prop = (v.get("proposition") or row.get("key", ""))[:80]
                items.append((conf, prop))
        items.sort(key=lambda x: x[0])
        if not items:
            return ""
        lines = [f"- {prop} (confidence {c:.2f})" for c, prop in items[:top_k]]
        return "\n[Uncertainty context — beliefs currently below high confidence:\n" + "\n".join(lines) + "]"
    except Exception:
        return ""
