"""
Internal red-team pass: rewrite draft as a single Technical Directive that satisfies constraints.
Does not expose adversary dialogue — only the final tightened spec.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine


def red_team_refine(
    engine: "CoreEngine",
    *,
    user_prompt: str,
    constraints: list[str],
    draft: str,
    max_tokens: int = 2048,
) -> str:
    """
    One LLM call: reject constraint violations, remove chat hedging, output TD only.
    """
    sys = """You are an internal red-team reviewer for sovereign infrastructure outputs.

Rules:
- Enforce the user's explicit constraints. If the draft violates a constraint, DELETE the violating content and replace with a compliant Technical Directive.
- Output ONLY the final Technical Directive (TD): sections, tables, imperative language.
- Banned in output: "I would", "it is likely", "simplified", "Assumptions:", "Limitations:" as filler, tutorial tone, Path A/Path B narration, Y/N checklists.
- Do not describe your review process. No meta. No preambles."""

    def _disp(x: str) -> str:
        if not x:
            return x
        if ":" in x:
            tag, rest = x.split(":", 1)
            if tag.strip().upper() in ("MUST", "FORBID", "LIMIT"):
                return rest.strip()
        return x

    cons_lines = (
        "\n".join(f"- {_disp(c)}" for c in (constraints or [])[:24])
        or "- (none explicitly parsed)"
    )
    user = (
        f"## User request (excerpt)\n{user_prompt[:2000]}\n\n"
        f"## Parsed constraints\n{cons_lines}\n\n"
        f"## Draft to vet and rewrite\n{draft[:14000]}"
    )
    try:
        out = engine.complete(
            [
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            temperature=0.12,
            max_tokens=max_tokens,
        )
        out = (out or "").strip()
        return out if len(out) > 80 else draft
    except Exception:
        return draft
