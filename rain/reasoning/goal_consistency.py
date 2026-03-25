"""
Goal consistency — ensure response aligns with current user goal (Tier 1.4).
Before returning, check that the response does not contradict the goal; retry or flag if it does.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

GOAL_ALIGNMENT_RETRY_INSTRUCTION = (
    "Your response must align with the user's stated goal. Do not contradict or oppose it. "
    "Output only the revised response."
)


def response_contradicts_goal(engine: "CoreEngine", goal: str, response: str, max_tokens: int = 20) -> bool:
    """
    Quick check: does the response contradict or oppose the user's goal?
    Returns True if it appears to contradict (so caller can retry or flag).
    Uses a short LLM call; on parse failure we assume no contradiction.
    """
    if not (goal or "").strip() or not (response or "").strip():
        return False
    goal = (goal or "").strip()[:400]
    resp_snippet = (response or "").strip()[:500]
    sys_msg = (
        "You judge goal alignment. Reply with ONLY one word: YES or NO. "
        "YES = the response contradicts or opposes the goal. NO = the response supports or is consistent with the goal."
    )
    user_msg = f"Goal: {goal}\n\nResponse: {resp_snippet}\n\nDoes the response contradict the goal? YES or NO."
    try:
        out = engine.complete(
            [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        out = (out or "").strip().upper()
        if re.search(r"\bYES\b", out):
            return True
        return False
    except Exception:
        return False
