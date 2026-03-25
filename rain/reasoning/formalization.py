"""
Tier 3: Compositional formalization — compose proof steps; validate structure.
"""
from __future__ import annotations
from typing import Any
from rain.reasoning.proof_fragment import verify_propositional_steps

def compose_proof_steps(steps: list[dict[str, Any]]) -> tuple[bool, str]:
    """Verify and compose steps into a single summary. Returns (valid, summary)."""
    if not steps:
        return True, ""
    ok, msg = verify_propositional_steps(steps)
    if not ok:
        return False, msg
    summary = "Composed proof: " + "; ".join((s.get("formula") or s.get("rule") or "")[:40] for s in steps[:10])
    return True, summary[:300]

def validate_steps_against_schema(steps: list[dict[str, Any]], required_keys: tuple[str, ...] = ("formula", "rule")) -> tuple[bool, str]:
    """Check each step has required keys. Returns (valid, message)."""
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            return False, f"Step {i+1} not a dict"
        for k in required_keys:
            if k not in s or not str(s.get(k)).strip():
                return False, f"Step {i+1} missing or empty: {k}"
    return True, "ok"
