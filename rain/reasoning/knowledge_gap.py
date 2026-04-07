"""
Knowledge gap detection — before answering, Rain explicitly identifies what it would
need to know to answer confidently. When critical gaps are large, it requests
clarification instead of confabulating. Small gaps proceed with a note.

Integrates with _verify_and_gate(): large gaps trigger a clarification response;
small gaps append a note to the answer.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

# How many critical gaps before we halt and ask for clarification
LARGE_GAP_THRESHOLD = 2


def detect_knowledge_gaps(
    engine: "CoreEngine",
    prompt: str,
    context: str = "",
) -> list[dict]:
    """
    Identify what Rain would need to know to answer the prompt confidently.

    Returns list of dicts: {gap, severity ("critical"|"minor"), suggestion}
    Empty list means Rain has sufficient information.
    """
    ctx_block = f"\nAvailable context:\n{context[:500]}" if context else ""
    detection_prompt = (
        f"You are assessing your own knowledge boundaries before answering.\n"
        f"{ctx_block}\n\n"
        f"Question to answer: {prompt[:400]}\n\n"
        f"Identify up to 3 specific pieces of information you would need to answer "
        f"this confidently and accurately. For each gap:\n"
        f"1. What specific fact, data, or context is missing?\n"
        f"2. Is it critical (would change the answer) or minor (would improve precision only)?\n"
        f"3. A brief suggestion for how the user could provide it.\n\n"
        f"Format:\n"
        f"GAP[N]: <what is missing>\n"
        f"Severity: <critical|minor>\n"
        f"Suggestion: <how to fill it>\n\n"
        f"If you have sufficient information to answer confidently, output only: SUFFICIENT\n\n"
        f"Output nothing else."
    )
    try:
        msgs = [{"role": "user", "content": detection_prompt}]
        raw = engine.complete(msgs, temperature=0.25, max_tokens=400)
    except Exception:
        return []

    raw = (raw or "").strip()
    if raw.upper().startswith("SUFFICIENT") or not raw:
        return []
    return _parse_gaps(raw)


def _parse_gaps(text: str) -> list[dict]:
    """Parse structured gap output into dicts."""
    blocks = re.split(r"\nGAP\d+:", "\n" + text)
    results: list[dict] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        gap = lines[0].strip() if lines else ""
        severity = "minor"
        suggestion = ""
        for line in lines[1:]:
            ll = line.strip()
            if ll.lower().startswith("severity:"):
                s = ll[9:].strip().lower()
                if s in ("critical", "minor"):
                    severity = s
            elif ll.lower().startswith("suggestion:"):
                suggestion = ll[11:].strip()
        if gap:
            results.append({
                "gap": gap[:200],
                "severity": severity,
                "suggestion": suggestion[:150],
            })
    return results


def should_request_clarification(gaps: list[dict]) -> bool:
    """True when critical gaps are numerous enough to justify halting."""
    critical = sum(1 for g in gaps if g.get("severity") == "critical")
    return critical >= LARGE_GAP_THRESHOLD


def format_clarification_request(gaps: list[dict]) -> str:
    """Format a clarification request when critical gaps are too large to proceed."""
    critical = [g for g in gaps if g["severity"] == "critical"]
    lines = ["To answer this accurately, I need a few more details:"]
    for i, g in enumerate(critical[:3], 1):
        line = f"  {i}. {g['gap']}"
        if g.get("suggestion"):
            line += f" — {g['suggestion']}"
        lines.append(line)
    return "\n".join(lines)


def format_gap_note(gaps: list[dict]) -> str:
    """Format minor gaps as a short note to append to the response."""
    if not gaps:
        return ""
    critical = [g for g in gaps if g["severity"] == "critical"]
    minor = [g for g in gaps if g["severity"] == "minor"]
    parts: list[str] = []
    if critical:
        parts.append("Critical unknowns: " + "; ".join(g["gap"] for g in critical[:2]))
    if minor:
        parts.append("Minor gaps: " + "; ".join(g["gap"] for g in minor[:2]))
    if not parts:
        return ""
    return "[Knowledge gaps noted: " + " | ".join(parts) + "]"
