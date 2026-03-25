"""Belief calibration — consistency checks for high-confidence beliefs.

When Rain records a belief with high confidence, we can probe for internal
consistency. If the model contradicts itself or expresses uncertainty,
downgrade the confidence.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine


# Confidence threshold above which we run consistency check
CALIBRATION_CONFIDENCE_THRESHOLD = 0.8

# Patterns indicating contradiction or uncertainty
CONTRADICTION_PATTERNS = [
    r"\b(?:actually|however|but)[\s,]*(?:no|not|that'?s wrong)\b",
    r"\bthat'?s\s+wrong\b",
    r"\bi\s+(?:was|may have been)\s+wrong\b",
    r"\b(?:not\s+entirely|not\s+quite|partially)\s+(?:correct|accurate|true)\b",
    r"\bit\s+depends\b",
]
UNCERTAINTY_PATTERNS = [
    r"\bi\s+(?:don'?t\s+)?(?:know|am not sure)\b",
    r"\b(?:uncertain|unclear|possibly|maybe)\b",
    r"\bi\s+(?:might|may)\s+have\s+(?:been\s+)?wrong\b",
    r"\b(?:could\s+be|might\s+be)\s+(?:wrong|incorrect)\b",
]


def _suggests_contradiction(text: str) -> bool:
    lower = text.lower()
    for pat in CONTRADICTION_PATTERNS:
        if re.search(pat, lower):
            return True
    return False


def _suggests_uncertainty(text: str) -> bool:
    lower = text.lower()
    for pat in UNCERTAINTY_PATTERNS:
        if re.search(pat, lower):
            return True
    return False


def check_belief_consistency(
    engine: "CoreEngine",
    claim: str,
    confidence: float,
    max_followups: int = 2,
) -> tuple[bool, float]:
    """
    Probe for internal consistency on a high-confidence belief.
    Returns (consistent, suggested_confidence).
    If consistent=False or suggested_confidence < confidence, downgrade.
    """
    if confidence < CALIBRATION_CONFIDENCE_THRESHOLD:
        return True, confidence

    prompts = [
        f"You previously stated: \"{claim[:200]}\" (confidence {confidence}). "
        "Is this still accurate? Any caveats? Answer in 1–2 sentences.",
        f"What would contradict or limit \"{claim[:150]}\"? Answer briefly.",
    ]
    downgrade = 0.0
    for i, prompt in enumerate(prompts[:max_followups]):
        try:
            response = engine.complete(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
            )
            if _suggests_contradiction(response):
                downgrade = max(downgrade, 0.3)
            elif _suggests_uncertainty(response):
                downgrade = max(downgrade, 0.15)
        except Exception:
            pass

    if downgrade > 0:
        suggested = max(0.2, confidence - downgrade)
        return False, round(suggested, 2)
    return True, confidence
