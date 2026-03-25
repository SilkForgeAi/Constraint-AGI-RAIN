"""
Constraint tracker — parse user constraints and verify every one is satisfied before answering.
Perfect reasoner fix: never silently drop a constraint when complexity is high.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

CONSTRAINT_PATTERNS = [
    r"(?:must|should|need to|required to)\s+([^.;]+?)(?:\.|;|$)",
    r"(?:under|within)\s+(\w+(?:\s+\w+)?)\s+(?:budget|limit)",
    r"(?:no|without)\s+([^.;]+?)(?:\.|;|$)",
    r"(?:support[s]?|with)\s+([^.;]+?)(?:\.|;|$)",
    r"(\d+)\s+constraints?\s*[:]",
    r"constraint\s*\d+\s*[:]\s*([^\n]+)",
]


def parse_constraints_from_prompt(prompt: str) -> list[str]:
    """Extract a list of constraint phrases from the user prompt."""
    if not (prompt or "").strip():
        return []
    p = (prompt or "").strip()
    out: list[str] = []
    seen: set[str] = set()
    for pat in CONSTRAINT_PATTERNS:
        for m in re.finditer(pat, p, re.I):
            c = (m.group(1) or m.group(0) or "").strip()[:80]
            c_lower = c.lower()
            if c and c_lower not in seen and len(c) > 2:
                seen.add(c_lower)
                out.append(c)
    # Also split on "and" / "," when we see "must be X and Y and Z"
    if " must " in p.lower() or " constraints" in p.lower():
        for part in re.split(r"\s+and\s+|\s*,\s*", p):
            part = part.strip()[:80]
            if part and ("must" in part.lower() or "no " in part.lower() or "under" in part.lower()):
                pl = part.lower()
                if pl not in seen:
                    seen.add(pl)
                    out.append(part)
    return out[:15]


def checklist_instruction(constraints: list[str]) -> str:
    """Return prompt instruction to map each user constraint into the final answer (no Y/N theatrics)."""
    if not constraints:
        return ""
    lines = [
        "Constraints from the user (address every one in your final output; use a numbered subsection or table row per item):",
    ]
    for i, c in enumerate(constraints, 1):
        lines.append(f"  {i}. {c}")
    lines.append(
        "Do not print interactive checklists (no “Satisfied? Y/N”). "
        "Integrate verification into the specification: state assumptions, limits, or explicit non-compliance where unavoidable."
    )
    return "\n".join(lines)


def response_satisfies_constraints(response: str, constraints: list[str]) -> tuple[bool, list[str]]:
    """
    Heuristic: check if response mentions satisfying or addressing each constraint.
    Returns (all_satisfied, list of constraint phrases that got no clear mention).
    """
    if not constraints:
        return True, []
    r = (response or "").lower()
    missing: list[str] = []
    for c in constraints:
        # Check if any significant word from constraint appears in response
        words = [w for w in c.lower().split() if len(w) > 3]
        if not words:
            continue
        if not any(w in r for w in words):
            missing.append(c)
    return (len(missing) == 0, missing)
