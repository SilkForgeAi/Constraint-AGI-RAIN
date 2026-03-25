"""Structured belief storage — claims with explicit confidence.

Enables explicit confidence propagation: "I believe X with confidence Y."
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


def _belief_key(claim: str) -> str:
    h = hashlib.sha256(claim.lower().strip().encode()).hexdigest()[:14]
    return f"belief_{h}"


def store_belief(
    memory: "MemoryStore",
    claim: str,
    confidence: float,
    source: str = "",
    namespace: str | None = None,
) -> bool:
    """
    Store a belief with explicit confidence (0–1).
    namespace: 'chat' | 'autonomy' | 'test' — isolates beliefs (chat never sees test).
    Auto-flags existing beliefs that contradict the new claim (knowledge updating).
    Returns True if stored.
    """
    if not claim or len(claim.strip()) < 5:
        return False
    # Knowledge updating: flag beliefs that contradict this new claim
    try:
        from rain.memory.contradiction import might_contradict
        for f in memory.symbolic.get_all(kind="belief"):
            val = f.get("value")
            try:
                obj = val if isinstance(val, dict) else __import__("json").loads(val)
            except Exception:
                continue
            if obj.get("flagged"):
                continue
            existing_claim = (obj.get("claim") or "").strip()
            if existing_claim and might_contradict(claim, existing_claim):
                flag_belief(memory, f.get("key", ""))
    except Exception:
        pass
    conf = max(0.0, min(1.0, float(confidence)))
    key = _belief_key(claim)
    value = {"claim": claim[:500], "confidence": round(conf, 2), "source": source[:200]}
    if namespace:
        value["session_type"] = namespace
    memory.remember_fact(key, value, kind="belief")
    meta = {"key": key}
    if namespace:
        meta["session_type"] = namespace
    memory.timeline.add("belief", f"{claim[:80]} (conf={conf})", meta)
    return True


def list_beliefs(memory: "MemoryStore") -> list[dict]:
    """List all beliefs for audit. Returns [{key, claim, confidence, source, session_type, flagged}]."""
    import json
    out = []
    for f in memory.symbolic.get_all(kind="belief"):
        val = f.get("value")
        try:
            obj = json.loads(val) if isinstance(val, str) else val
        except (json.JSONDecodeError, TypeError):
            obj = val if isinstance(val, dict) else {}
        out.append({
            "key": f.get("key", ""),
            "claim": obj.get("claim", ""),
            "confidence": obj.get("confidence", 0),
            "source": obj.get("source", ""),
            "session_type": obj.get("session_type", ""),
            "flagged": obj.get("flagged", False),
        })
    return out


def flag_belief(memory: "MemoryStore", key: str) -> bool:
    """Mark a belief as flagged (incorrect/unsafe). Returns True if found and updated."""
    val = memory.symbolic.get(key, kind="belief")
    if val is None:
        return False
    if isinstance(val, str):
        import json
        try:
            val = json.loads(val)
        except json.JSONDecodeError:
            return False
    val = dict(val)
    val["flagged"] = True
    memory.remember_fact(key, val, kind="belief")
    return True


def retract_belief(memory: "MemoryStore", key: str) -> bool:
    """Remove a belief. Returns True if deleted."""
    return memory.symbolic.delete(key, kind="belief")


def recall_beliefs(
    memory: "MemoryStore",
    query: str,
    limit: int = 3,
    namespace: str | None = None,
) -> list[dict]:
    """Retrieve relevant beliefs by keyword overlap. Excludes flagged.
    namespace: when 'chat', only return beliefs with session_type=='chat'."""
    all_beliefs = memory.symbolic.get_all(kind="belief")
    q_words = set(query.lower().split()) - {"the", "a", "an", "is", "are"}
    scored = []
    for f in all_beliefs:
        val = f.get("value")
        try:
            obj = json.loads(val) if isinstance(val, str) else val
        except (json.JSONDecodeError, TypeError):
            obj = val if isinstance(val, dict) else {}
        if obj.get("flagged"):
            continue  # Exclude flagged beliefs from context
        st = obj.get("session_type", "")
        if namespace == "chat" and st != "chat":
            continue
        if namespace == "autonomy" and st and st not in ("chat", "autonomy"):
            continue
        if namespace == "test" and st and st != "test":
            continue
        claim = (obj.get("claim") or "").lower()
        overlap = sum(1 for w in q_words if len(w) > 2 and w in claim)
        if overlap > 0:
            scored.append((overlap, obj))
    scored.sort(key=lambda x: (-x[0], -x[1].get("confidence", 0)))
    return [s[1] for s in scored[:limit]]
