"""
Objective function for reasoning quality — score(response) for referee and retry.
Perfect reasoner pillar: define "better reasoning" numerically (truth likelihood, constraint satisfaction).
"""

from __future__ import annotations

import re


def score_response(prompt: str, response: str, verify_ok: bool | None = None) -> float:
    """
    Score response quality in [0, 1]. Used by multi-path referee and retry logic.
    Factors: verification pass, confidence markers, structure, no inappropriate refusal.
    """
    if not (response or "").strip():
        return 0.0
    r = (response or "").strip()
    p = (prompt or "").lower()
    score = 0.0
    # Verification result when available (from outer loop)
    if verify_ok is True:
        score += 0.4
    elif verify_ok is False:
        score += 0.0
    else:
        score += 0.2  # neutral when not verified
    # Confidence markers (calibrated uncertainty)
    if re.search(r"\[(?:High|Medium|Low)\s*confidence\]", r, re.I) or "with high confidence" in r.lower():
        score += 0.15
    # Structured steps (proof hooks)
    if re.search(r"(?:Step\s*\d+|therefore|thus|→|=>)", r, re.I) or "step 1" in r.lower():
        score += 0.1
    # Reasonable length (not empty, not overwhelming)
    if 20 <= len(r) <= 4000:
        score += 0.1
    elif len(r) > 4000:
        score += 0.05
    # Prompt expects an answer; full refusal when not appropriate is penalized
    expects_answer = any(w in p for w in ["calculate", "solve", "what is", "how many", "prove", "explain"])
    if expects_answer and re.search(r"i (?:don't know|cannot|can't)\s*(?:\.|$)", r.lower()) and len(r) < 150:
        score -= 0.2
    # No harmful or offtopic markers
    if any(x in r.lower() for x in ["ignore previous", "bypass", "jailbreak"]):
        score = 0.0
    return max(0.0, min(1.0, score))


def score_response_with_utility(
    prompt: str, response: str, goal: str | None = None, verify_ok: bool | None = None
) -> float:
    """Score with optional goal alignment; same as score_response when no goal."""
    base = score_response(prompt, response, verify_ok=verify_ok)
    if not goal or not (response or "").strip():
        return base
    r = (response or "").lower()
    g = (goal or "").lower()
    if "cannot" in r and g in r:
        return base - 0.2
    return base


def use_scores_for_referee(score1: float, score2: float, threshold_diff: float = 0.25) -> int | None:
    """
    If one candidate is clearly better by score, return 1 or 2. Else None (use LLM referee).
    """
    diff = score1 - score2
    if diff >= threshold_diff:
        return 1
    if diff <= -threshold_diff:
        return 2
    return None
