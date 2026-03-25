"""
Tier 3: Calibration — confidence aligned with correctness.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

DEFER_SUGGESTION = " [Calibration: high-confidence claim; verify independently if critical.]"

def has_high_confidence_markers(response: str) -> bool:
    if not (response or "").strip():
        return False
    r = (response or "").lower()
    return bool(
        re.search(r"\[(?:High|high)\s*confidence\]", response) or "with high confidence" in r
        or "certain that" in r or "definitely" in r
    ) and "uncertain" not in r[:200]

def calibration_check(engine: "CoreEngine", response: str, prompt: str, verify_ran: bool, verify_ok: bool | None, max_tokens: int = 60) -> tuple[str, bool]:
    if not has_high_confidence_markers(response):
        return "", False
    if verify_ran and verify_ok is True:
        return "", False
    try:
        out = engine.complete(
            [{"role": "system", "content": "Reply ADD_NOTE or OK. ADD_NOTE if strong unverified claim."},
             {"role": "user", "content": f"Prompt: {prompt[:200]}. Response: {response[:300]}. Verify_ok: {verify_ok}. ADD_NOTE or OK?"}],
            temperature=0.0, max_tokens=max_tokens)
        if "ADD_NOTE" in (out or "").upper():
            return DEFER_SUGGESTION, True
    except Exception:
        pass
    return "", False

def record_outcome(memory, proposition: str, was_correct: bool, namespace: str | None = None) -> None:
    try:
        from rain.reasoning.belief_slice import update as belief_update
        belief_update(memory, (proposition or "")[:200], 0.4, supported=was_correct, namespace=namespace)
    except Exception:
        pass
