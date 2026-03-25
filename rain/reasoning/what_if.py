"""
What-if / interventional reasoning — Tier 2: lightweight SCM (real "what if").

Detects "what if", "suppose that", "if we had" style queries and answers under
an explicit intervention. Bounded conclusion with disclaimer.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

WHAT_IF_PATTERNS = [
    r"what\s+if\s+(.+?)(?:\?|$)",
    r"suppose\s+(?:that\s+)?(.+?)(?:\.|\?|$)",
    r"if\s+(?:we\s+)?had\s+(.+?)(?:\s*,\s*|\?|$)",
    r"assuming\s+(.+?)(?:\s*,\s*|\.|\?|$)",
]

DISCLAIMER = " [Bounded: hypothetical intervention; not a prediction.]"


def detect_what_if(prompt: str) -> str | None:
    """Extract the intervention clause if prompt is a what-if style query."""
    if not (prompt or "").strip():
        return None
    p = (prompt or "").strip()
    for pat in WHAT_IF_PATTERNS:
        m = re.search(pat, p, re.I | re.S)
        if m:
            intervention = m.group(1).strip()[:300]
            if len(intervention) > 5:
                return intervention
    return None


def query_what_if(
    engine: "CoreEngine",
    prompt: str,
    intervention: str,
    context: str = "",
    max_tokens: int = 512,
) -> tuple[str, str]:
    """
    Answer under explicit intervention. Returns (answer_snippet, disclaimer).
    Uses one LLM call with strict framing: intervention only; label as hypothetical.
    """
    sys_msg = (
        "You answer counterfactual or hypothetical questions. "
        "Given an intervention (something we assume or suppose), reason about what would follow. "
        'Be concise. Start your answer with [Intervention result]: and end with "[Bounded: hypothetical intervention; not a prediction.]"'
    )
    user_msg = f"Intervention: {intervention}\n\nQuestion: {prompt[:400]}\n\nAnswer under this intervention only."
    if context:
        user_msg = f"Context: {context[:200]}\n\n" + user_msg
    try:
        out = engine.complete(
            [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        out = (out or "").strip()
        if DISCLAIMER.strip() not in out:
            out = out + DISCLAIMER
        return out, DISCLAIMER.strip()
    except Exception:
        return "", DISCLAIMER.strip()
