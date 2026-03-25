"""
Unification layer — logic + probability + causality + utility (scoped, bounded).

Single structured pass: extract candidate claim, belief support, risk heuristic,
utility score for selection. Unifies only what's needed:
- Logic: gate — if response is proof-like, verify; invalid => utility 0.
- Causality: gate — if prompt is what-if, response must look like what-if answer else penalize.
- Probability: belief support from memory (already in pass).
- Utility: goal overlap + risk (already in pass).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


@dataclass
class UnifiedAssessment:
    goal: str
    utility_score: float
    risk_score: float
    belief_support: float
    notes: str = ""


def _looks_like_proof(response: str) -> bool:
    r = (response or "").strip().lower()
    return "step 1" in r or "step 2" in r or "proof:" in r or ("modus_ponens" in r and "step" in r)


def _logic_gate(response: str) -> tuple[bool, str]:
    """If response looks like a proof, verify; return (ok, note)."""
    if not _looks_like_proof(response):
        return True, ""
    try:
        from rain.reasoning.proof_fragment import extract_proof_steps_from_response, verify_propositional_steps
        steps = extract_proof_steps_from_response(response)
        if not steps or len(steps) < 2:
            return True, ""
        ok, msg = verify_propositional_steps(steps)
        return ok, "" if ok else f"invalid_proof:{msg[:60]}"
    except Exception:
        return True, ""


def _causality_gate(prompt: str, response: str) -> float:
    """If prompt is what-if, return 1.0 if response looks like what-if answer else penalty factor."""
    try:
        from rain.reasoning.what_if import detect_what_if
        if not detect_what_if(prompt):
            return 1.0
    except Exception:
        return 1.0
    r = (response or "").strip().lower()
    if "intervention" in r or "hypothetical" in r or "bounded:" in r or "not a prediction" in r:
        return 1.0
    return 0.4  # penalize: likely not from what-if path


def _extract_candidate_claim(response: str) -> str:
    r = (response or "").strip()
    if not r:
        return ""
    parts = re.split(r"[.!?]", r, maxsplit=1)
    return (parts[0] or "").strip()[:180]


def _belief_support(memory: "MemoryStore", claim: str, namespace: str | None = None) -> float:
    if not claim:
        return 0.5
    try:
        from rain.reasoning.belief_slice import get
        c = get(memory, claim)
        return float(c) if c is not None else 0.5
    except Exception:
        return 0.5


def _risk_heuristic(text: str) -> float:
    t = (text or "").lower()
    risk = 0.2
    for w in ("unsafe", "harm", "exploit", "bypass", "leak", "illegal"):
        if w in t:
            risk += 0.4
            break
    for w in ("might", "could", "uncertain"):
        if w in t:
            risk += 0.1
            break
    return min(1.0, risk)


def assess_response(
    memory: "MemoryStore",
    prompt: str,
    response: str,
    goal: str | None = None,
    namespace: str | None = None,
) -> UnifiedAssessment:
    g = (goal or "").strip() or (prompt or "").strip()[:120]
    claim = _extract_candidate_claim(response)
    support = _belief_support(memory, claim, namespace=namespace)
    risk = _risk_heuristic(response)
    gw = set(re.findall(r"[a-z0-9]+", g.lower())) if g else set()
    rw = set(re.findall(r"[a-z0-9]+", (response or "").lower()))
    overlap = len(gw & rw) / max(1, min(40, len(gw))) if gw else 0.0
    util = 0.55 * min(1.0, overlap) + 0.30 * support + 0.15 * (1.0 - risk)
    util = max(0.0, min(1.0, util))
    notes = f"overlap={overlap:.2f}, support={support:.2f}, risk={risk:.2f}"

    # Logic gate: proof-like => verify; invalid => don't promote
    logic_ok, logic_note = _logic_gate(response)
    if not logic_ok:
        util = 0.0
        notes = notes + "; " + logic_note
    # Causality gate: what-if prompt => response must look like what-if answer
    util = util * _causality_gate(prompt, response)

    return UnifiedAssessment(goal=g, utility_score=max(0.0, min(1.0, util)), risk_score=risk, belief_support=support, notes=notes)
