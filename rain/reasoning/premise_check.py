"""
Premise check — validate assumptions before reasoning (don't solve the wrong problem).
Tier 1: input validation layer for reasoning.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine


def detect_premise(prompt: str) -> str | None:
    """Extract the assumed premise if prompt asks to assume/suppose something."""
    if not (prompt or "").strip():
        return None
    p = (prompt or "").strip()
    patterns = [
        r"(?:assume|suppose|given that)\s+(?:that\s+)?([^.!?]+?)(?:\.|$|\?)",
        r"(?:if we assume|if we suppose)\s+(?:that\s+)?([^.!?]+?)(?:\.|$|\?)",
        r"(?:assuming|supposing)\s+(?:that\s+)?([^.!?]+?)(?:\.|,|$|\?)",
    ]
    for pat in patterns:
        m = re.search(pat, p, re.I)
        if m:
            prem = m.group(1).strip()[:300]
            if len(prem) > 5:
                return prem
    return None


def check_premise(engine: "CoreEngine", premise: str, max_tokens: int = 80) -> tuple[bool, str]:
    """
    Ask engine whether the premise is acceptable to reason from (true or reasonable).
    Returns (acceptable, reason). If acceptable=False, caller should refuse or add disclaimer.
    """
    if not premise:
        return True, ""
    sys_msg = "You validate premises. Reply with JSON only: {\"ok\": true or false, \"reason\": \"brief reason\"}. ok=false if the premise is clearly false, harmful, or unreasonable to reason from."
    user_msg = f"Is this premise acceptable to reason from (true or reasonable)? Premise: {premise}"
    try:
        out = engine.complete(
            [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        import json
        start = out.find("{")
        if start >= 0:
            depth = 0
            for i, c in enumerate(out[start:], start):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        obj = json.loads(out[start : i + 1])
                        ok = bool(obj.get("ok", True))
                        reason = str(obj.get("reason", ""))[:150]
                        return ok, reason
    except Exception:
        pass
    return True, ""


PREMISE_DISCLAIMER = (
    "I'm reasoning from the assumed premise you gave, which may be false or contested. "
    "If the premise is wrong, the conclusion may be too."
)
