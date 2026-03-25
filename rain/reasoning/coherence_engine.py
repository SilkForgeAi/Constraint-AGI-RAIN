"""
Global coherence engine — contradiction resolution + bounded belief propagation.

Detect contradictions between new claim and stored beliefs; resolve by lowering
confidence of weaker/older; optional bounded propagation. Heuristic but systematic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


@dataclass
class CoherenceResult:
    ok: bool
    message: str
    changed: bool = False


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())[:180]


def _negation_pair(a: str, b: str) -> bool:
    a, b = _normalize(a), _normalize(b)
    if not a or not b or a == b:
        return False
    a_not = " not " in (" " + a + " ") or a.startswith("not ")
    b_not = " not " in (" " + b + " ") or b.startswith("not ")
    if a_not == b_not:
        return False
    ta = set(re.findall(r"[a-z0-9]+", a.replace("not", "")))
    tb = set(re.findall(r"[a-z0-9]+", b.replace("not", "")))
    return len(ta) >= 2 and len(tb) >= 2 and len(ta & tb) >= 2


def resolve_and_propagate(
    memory: "MemoryStore",
    new_claim: str,
    namespace: str | None = None,
) -> CoherenceResult:
    """Resolve contradictions; optionally soften or reinforce beliefs."""
    claim = (new_claim or "").strip()[:200]
    if not claim:
        return CoherenceResult(ok=True, message="no claim", changed=False)
    try:
        from rain.reasoning.belief_slice import get as belief_get, update as belief_update
    except Exception:
        return CoherenceResult(ok=True, message="belief layer unavailable", changed=False)

    beliefs: list[tuple[str, float]] = []
    try:
        raw: object
        if hasattr(memory.symbolic, "list"):
            raw = getattr(memory.symbolic, "list")(kind="belief")
        else:
            raw = getattr(memory.symbolic, "get_all")(kind="belief")
        if isinstance(raw, list):
            for item in raw[:60]:
                if not isinstance(item, dict):
                    continue
                v = item.get("value", item)
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except Exception:
                        v = {}
                if isinstance(v, dict):
                    prop = (v.get("proposition") or item.get("proposition") or "").strip()
                    conf = float(v.get("confidence", item.get("confidence", 0.5)))
                    if prop:
                        beliefs.append((prop[:200], conf))
    except Exception:
        pass


    for prop, conf in beliefs:
        if _negation_pair(prop, claim):
            c_conf = belief_get(memory, claim)
            c_conf = float(c_conf) if c_conf is not None else 0.5
            if c_conf > conf + 0.05:
                belief_update(memory, prop, 0.35, supported=False, namespace=namespace)
                return CoherenceResult(ok=False, message=f"contradiction resolved: lowered '{prop[:50]}...'", changed=True)
            if conf > c_conf + 0.05:
                belief_update(memory, claim, 0.35, supported=False, namespace=namespace)
                return CoherenceResult(ok=False, message=f"contradiction resolved: lowered new claim", changed=True)
            belief_update(memory, prop, 0.2, supported=False, namespace=namespace)
            belief_update(memory, claim, 0.2, supported=False, namespace=namespace)
            return CoherenceResult(ok=False, message="contradiction detected; softened both", changed=True)

    try:
        from rain.reasoning.belief_slice import update as belief_update
        belief_update(memory, claim, 0.15, supported=True, namespace=namespace)
        return CoherenceResult(ok=True, message="ok", changed=True)
    except Exception:
        return CoherenceResult(ok=True, message="ok", changed=False)
