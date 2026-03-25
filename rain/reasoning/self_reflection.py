"""Recursive Self-Reflection — belief revision, reasoning critique, internal debate.

Belief revision: update confidence given evidence.
Reasoning critique: check whether a step supports a conclusion.
Internal debate: multiple views then aggregate (wraps multi_agent or simple multi-call).
"""

from __future__ import annotations

from typing import Any


def belief_revision(
    claim: str,
    evidence: str,
    current_confidence: float,
    engine: Any,
) -> float:
    """
    Given a claim, new evidence, and current confidence (0-1), return revised confidence.
    Uses a single LLM call to output a number 0.0-1.0 or a short rationale then parse.
    """
    prompt = f"""Claim: {claim}
Current confidence in claim (0-1): {current_confidence}
New evidence: {evidence}

Should confidence increase, decrease, or stay the same? Output ONLY a single number between 0.0 and 1.0 (revised confidence). No explanation."""

    try:
        out = engine.complete(
            [
                {"role": "system", "content": "Output only a decimal number between 0 and 1."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=20,
        ).strip()
        import re
        match = re.search(r"0?\.\d+|\d+\.\d+|[01]", out)
        if match:
            v = float(match.group())
            return max(0.0, min(1.0, v))
    except Exception:
        pass
    return current_confidence


def reasoning_critique(
    step: str,
    conclusion: str,
    engine: Any,
) -> tuple[bool, list[str]]:
    """
    Check whether the step supports the conclusion. Returns (valid, list of issues).
    If valid is False, issues list non-empty with reasons.
    """
    prompt = f"""Step or reasoning: {step}
Conclusion: {conclusion}

Does the step logically support the conclusion? Consider: logical validity, hidden assumptions, gaps.
Output JSON only: {{"valid": true or false, "issues": ["issue1", "issue2"]}}
If valid is true, issues can be empty []."""

    try:
        out = engine.complete(
            [
                {"role": "system", "content": "Output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        ).strip()
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
                        if isinstance(obj, dict):
                            valid = obj.get("valid", False)
                            issues = obj.get("issues") or []
                            if isinstance(issues, list):
                                issues = [str(x) for x in issues]
                            else:
                                issues = []
                            return (valid, issues)
                        break
    except Exception:
        pass
    return (False, ["Critique parse failed."])


def internal_debate(
    question: str,
    engine: Any,
    context: str = "",
    n_views: int = 3,
    aggregate: str = "chair",
) -> tuple[str, list[str]]:
    """
    Generate n_views different answers (e.g. via multi_agent), then aggregate.
    Returns (final_answer, list of view answers).
    """
    from rain.reasoning.multi_agent_cognition import reason_multi_agent
    return reason_multi_agent(
        question,
        engine,
        context=context,
        n_agents=n_views,
        aggregate=aggregate,
    )
