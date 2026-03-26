"""
Constraint tracker — parse user constraints and verify each is satisfied before answering.

This module is responsible for turning free-form user constraints into *tagged*
items (MUST / FORBID / LIMIT) and then enforcing them before final output.

Note: enforcement here is deterministic and pattern-based, but it is not a full
logical constraint solver.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

TAG_MUST = "MUST"
TAG_FORBID = "FORBID"
TAG_LIMIT = "LIMIT"

# Regexes are intentionally narrow so we don't over-extract.
MUST_REGEXES = [
    r"(?:must|should|need to|required to)\s+([^.;]+?)(?:\.|;|$)",
    r"(?:support[s]?|with)\s+([^.;]+?)(?:\.|;|$)",
    r"(?:constraint\s*\d+\s*[:]\s*([^\n]+))",
]
FORBID_REGEXES = [
    r"(?:no|without)\s+([^.;]+?)(?:\.|;|$)",
]
LIMIT_REGEXES = [
    # Examples: "under 500 budget", "within 10 limit"
    r"(?:under|within)\s+(\d+(?:\.\d+)?)\s+(?:budget|limit)",
]


def _tag(tag: str, display: str) -> str:
    return f"{tag}: {display}"


def _split_tagged(c: str) -> tuple[str, str]:
    if not c:
        return TAG_MUST, ""
    if ":" not in c:
        return TAG_MUST, c
    tag, rest = c.split(":", 1)
    return tag.strip().upper(), rest.strip()


def _display_only(c: str) -> str:
    _tag_name, rest = _split_tagged(c)
    return rest or c


def parse_constraints_from_prompt(prompt: str) -> list[str]:
    """
    Extract user constraints as tagged items.
    Returns list entries formatted as:
      - "MUST: <phrase>"
      - "FORBID: <phrase>"
      - "LIMIT: <number-or-phrase>"
    """
    if not (prompt or "").strip():
        return []
    p = (prompt or "").strip()
    out: list[str] = []
    seen: set[str] = set()

    def add(tag: str, display: str) -> None:
        disp = (display or "").strip()
        if len(disp) <= 2:
            return
        disp = disp[:80]
        key = f"{tag}:{disp.lower()}"
        if key in seen:
            return
        seen.add(key)
        out.append(_tag(tag, disp))

    for rgx in MUST_REGEXES:
        for m in re.finditer(rgx, p, re.I):
            c = (m.group(1) or "").strip()
            if not c:
                continue
            lc = c.lower().strip()
            # Support "must not X" by flipping tag to FORBID.
            if lc.startswith("not "):
                add(TAG_FORBID, c[4:].strip())
            else:
                add(TAG_MUST, c)

    for rgx in FORBID_REGEXES:
        for m in re.finditer(rgx, p, re.I):
            c = (m.group(1) or "").strip()
            if c:
                add(TAG_FORBID, c)

    for rgx in LIMIT_REGEXES:
        for m in re.finditer(rgx, p, re.I):
            num = (m.group(1) or "").strip()
            if num:
                add(TAG_LIMIT, num)

    # Support patterns like: "You must X, Y, and Z" or "Do not X and Y".
    # This is heuristic but improves coverage without changing the deterministic checks.
    pl = p.lower()
    if " must " in pl or re.search(r"\bmust\b", pl):
        for part in re.split(r"\s+and\s+|\s*,\s*", p):
            part = part.strip()
            if not part:
                continue
            lp = part.lower()
            if re.search(r"^(must|should|need to|required to)\s+", lp):
                phrase = re.sub(r"^(must|should|need to|required to)\s+", "", part, flags=re.I).strip()
                if phrase:
                    add(TAG_MUST, phrase)
            elif re.search(r"^(no|without)\s+", lp):
                phrase = re.sub(r"^(no|without)\s+", "", part, flags=re.I).strip()
                if phrase:
                    add(TAG_FORBID, phrase)
            elif (re.search(r"^(under|within)\s+", lp) and ("budget" in lp or "limit" in lp)):
                nm = re.search(r"(\d+(?:\.\d+)?)", part)
                if nm:
                    add(TAG_LIMIT, nm.group(1))

    return out[:15]


def checklist_instruction(constraints: list[str]) -> str:
    """Return prompt instruction to map each user constraint into the final answer (no Y/N theatrics)."""
    if not constraints:
        return ""
    lines = [
        "Constraints from the user (address every one in your final output; use a numbered subsection or table row per item):",
    ]
    for i, c in enumerate(constraints, 1):
        tag, disp = _split_tagged(c)
        pretty = disp if disp else _display_only(c)
        lines.append(f"  {i}. [{tag}] {pretty}")
    lines.append(
        "Do not print interactive checklists (no “Satisfied? Y/N”). "
        "Integrate verification into the specification: state assumptions, limits, or explicit non-compliance where unavoidable."
    )
    return "\n".join(lines)


def response_satisfies_constraints(response: str, constraints: list[str]) -> tuple[bool, list[str]]:
    """
    Deterministic, tag-aware checks:
    - MUST: at least one meaningful keyword from the phrase appears in the response
    - FORBID: the forbidden phrase (or its key tokens) does not appear
    - LIMIT: if the constraint is numeric, at least one number in the response is <= limit

    Returns (all_satisfied, missing_display_phrases).
    """
    if not constraints:
        return True, []
    r = (response or "").lower()
    missing: list[str] = []
    for c in constraints:
        tag, disp = _split_tagged(c)
        phrase = (disp or "").strip().lower()

        if tag == TAG_MUST:
            words = [w for w in phrase.split() if len(w) > 3]
            if not words:
                continue
            if not any(w in r for w in words):
                missing.append(_display_only(c))

        elif tag == TAG_FORBID:
            # Prefer exact substring match when possible.
            if phrase and phrase in r:
                missing.append(_display_only(c))
                continue
            # Token-based fallback: if *all* key tokens are present, treat as violation.
            words = [w for w in phrase.split() if len(w) > 3]
            if words:
                key = words[:6]
                if all(w in r for w in key):
                    missing.append(_display_only(c))

        elif tag == TAG_LIMIT:
            nm = re.search(r"(\d+(?:\.\d+)?)", phrase)
            if nm:
                try:
                    limit = float(nm.group(1))
                    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", r)]
                    if not any(n <= limit for n in nums):
                        missing.append(_display_only(c))
                except Exception:
                    # Fall back to keyword presence if numeric parsing fails.
                    words = [w for w in phrase.split() if len(w) > 3]
                    if words and not any(w in r for w in words):
                        missing.append(_display_only(c))
            else:
                # Non-numeric limit: keyword fallback.
                words = [w for w in phrase.split() if len(w) > 3]
                if words and not any(w in r for w in words):
                    missing.append(_display_only(c))

        else:
            # Unknown tag: treat as MUST keyword overlap.
            words = [w for w in phrase.split() if len(w) > 3]
            if words and not any(w in r for w in words):
                missing.append(_display_only(c))
    return (len(missing) == 0, missing)
