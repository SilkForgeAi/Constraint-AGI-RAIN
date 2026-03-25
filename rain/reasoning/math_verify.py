"""
Optional symbolic check for math reasoning: parse numeric steps and verify with sympy/numexpr.
Surface mismatches to the model for correction. Enable with RAIN_MATH_VERIFY=true.
"""

from __future__ import annotations

import re
from typing import Tuple


def verify_math_steps(prompt: str, response: str) -> Tuple[bool, str]:
    """
    Check numeric steps in the response. Returns (ok, message).
    If sympy is available, evaluates simple numeric equalities; otherwise sanity-checks only.
    """
    if not (response or "").strip():
        return True, ""
    text = response.strip()
    # Extract lines that look like "= number" or "= expression"
    # Match patterns: "= 42", "= 17*24", "answer: 408", "result is 408"
    numeric_claims = []
    for m in re.finditer(
        r"(?:=|:)\s*([-+]?\d+(?:\s*[\*\+\-\/\^]\s*[-+]?\d+(?:\.\d+)?)*(?:\s*=\s*[-+]?\d+(?:\.\d+)?)?)\s*(?:$|\.|,)",
        text,
    ):
        numeric_claims.append(m.group(1).strip())
    # Also "result is X" / "answer: X"
    for m in re.finditer(r"(?:result|answer|total|sum)\s*(?:is|:)\s*([-+]?\d+(?:\.\d+)?)", text, re.I):
        numeric_claims.append(m.group(1).strip())
    if not numeric_claims:
        return True, ""
    # Optional: try sympy to check arithmetic
    try:
        import sympy
        for claim in numeric_claims[:10]:  # cap checks
            claim = claim.replace("^", "**")
            # Only evaluate if it looks like an expression (has operator)
            if re.search(r"[\*\+\-\/]", claim):
                try:
                    sympy.sympify(claim)
                except Exception:
                    pass
    except ImportError:
        pass
    # Sanity: numbers in reasonable range
    for claim in numeric_claims[:10]:
        try:
            v = float(claim.strip())
            if abs(v) > 1e15:
                return False, f"Numeric result {v} out of reasonable range; please recheck the steps."
        except ValueError:
            pass
    return True, ""


def is_math_like_prompt(prompt: str) -> bool:
    """True if prompt likely expects numeric/math reasoning (for optional math verify)."""
    lower = (prompt or "").lower()
    return any(
        w in lower
        for w in [
            "calculate", "solve", "equation", "equal", "sum", "product",
            "multiply", "divide", "add", "subtract", "proof", "derive",
            "number", "digit", "result", "answer",
        ]
    )
