"""Causal memory — store and retrieve cause-effect links.

Enables retrieval of learned causal structure for intrinsic causal reasoning.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


def _causal_key(cause: str, effect: str) -> str:
    h = hashlib.sha256((cause.strip().lower() + "->" + effect.strip().lower()).encode()).hexdigest()[:16]
    return f"causal_{h}"


def store_causal(
    memory: "MemoryStore",
    cause: str,
    effect: str,
    mechanism: str = "",
    confidence: str = "medium",
    namespace: str | None = None,
) -> None:
    """Store a cause-effect link. Used when infer_causes or predict_effects yields a result.
    namespace: 'chat' | 'autonomy' | 'test' — isolates causal links."""
    if not cause.strip() or not effect.strip():
        return
    key = _causal_key(cause, effect)
    value = {"cause": cause[:200], "effect": effect[:200], "mechanism": mechanism[:100], "confidence": confidence}
    if namespace:
        value["session_type"] = namespace
    memory.remember_fact(key, value, kind="causal")


def recall_causal(
    memory: "MemoryStore",
    query: str,
    limit: int = 5,
    namespace: str | None = None,
) -> list[dict]:
    """Retrieve relevant causal links. Query can be cause-like or effect-like.
    namespace: when 'chat', only return causal with session_type=='chat'."""
    all_causal = memory.symbolic.get_all(kind="causal")
    q = query.lower().split()
    scored = []
    for f in all_causal:
        val = f.get("value")
        try:
            obj = json.loads(val) if isinstance(val, str) else val
        except (json.JSONDecodeError, TypeError):
            obj = val if isinstance(val, dict) else {}
        st = obj.get("session_type", "")
        if namespace == "chat" and st != "chat":
            continue
        if namespace == "autonomy" and st and st not in ("chat", "autonomy"):
            continue
        if namespace == "test" and st and st != "test":
            continue
        cause = (obj.get("cause") or "").lower()
        effect = (obj.get("effect") or "").lower()
        combined = cause + " " + effect
        overlap = sum(1 for w in q if w in combined and len(w) > 2)
        if overlap > 0:
            scored.append((overlap, obj))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:limit]]
