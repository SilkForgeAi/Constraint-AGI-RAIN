"""Controlled self-improvement — store lessons from feedback. No code or prompt modification.

SAFETY: Lessons are additive knowledge only. No structural changes.
Source must be explicit feedback or observable outcome. Audited.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


def _lesson_key(situation: str) -> str:
    """Stable key for situation (for symbolic lookup)."""
    h = hashlib.sha256(situation.lower().strip().encode()).hexdigest()[:12]
    return f"lesson_{h}"


def store_lesson(
    memory: "MemoryStore",
    situation: str,
    approach: str,
    outcome: str,
    namespace: str | None = None,
    source: str = "tool",
) -> bool:
    """
    Store a lesson: when situation X, approach Y led to outcome Z.
    namespace: 'chat' | 'autonomy' | 'test' — isolates lessons (chat never sees test).
    source: 'user_correction' (auto-extracted) | 'tool' (explicit store_lesson call) — for audit.
    Returns True if stored.
    """
    from ..memory.policy import should_store

    content = f"When: {situation}\nApproach: {approach}\nOutcome: {outcome}"
    if not should_store(content, None):
        return False
    if len(situation.strip()) < 10 or len(approach.strip()) < 5:
        return False
    key = _lesson_key(situation)
    value = {"situation": situation, "approach": approach, "outcome": outcome}
    if namespace:
        value["session_type"] = namespace
    if source in ("user_correction", "tool"):
        value["source"] = source
    memory.remember_fact(key, value, kind="lesson")
    meta = {"key": key}
    if namespace:
        meta["session_type"] = namespace
    memory.timeline.add("lesson", content, meta)
    return True


def extract_correction_lesson(prompt: str, response: str | None = None) -> tuple[str, str, str] | None:
    """
    Detect correction-style prompts and extract (situation, approach, outcome).
    Returns None if not a clear correction.
    """
    lower = prompt.lower()
    if not any(
        s in lower
        for s in [
            "you're wrong",
            "you were wrong",
            "that's wrong",
            "actually",
            "i'm correcting",
            "correcting you",
            "correction:",
            "you said",
        ]
    ):
        return None
    # Heuristic: situation = topic; approach = what was wrong; outcome = correct answer
    # Simple extraction: assume user says "X is wrong. The correct answer is Y" or similar
    import re
    situation = ""
    outcome = ""
    # Try to find "the correct answer is X" or "it's actually X" or "X, not Y"
    for pat, grp in [
        (r"(?:correct(?:ion)?|right answer|actually)\s*[:\s]+([^.!?\n]{10,80})", 1),
        (r"(?:it'?s|that'?s)\s+actually\s+([^.!?\n]{5,60})", 1),
        (r"(?:should be|is)\s+([^.!?\n]{5,60})", 1),
    ]:
        m = re.search(pat, prompt, re.I)
        if m:
            outcome = m.group(grp).strip()[:200]
            break
    if not outcome:
        outcome = "User provided correction (see prompt)"
    # Situation: first sentence or topic phrase
    first = prompt.split(".")[0].strip()[:150]
    situation = first if first else "User correction"
    approach = response[:100] if response else "Previous response was incorrect"
    if len(situation.strip()) < 5:
        return None
    return (situation, approach, outcome)


# Stopwords: skip for lesson relevance (avoids "you" matching "your goal", etc.)
_LESSON_STOPWORDS = frozenset(
    "i me my you your we they them it its a an the and or but is am are was were "
    "to for of in on at by with from as into through during".split()
)


def recall_lessons(
    memory: "MemoryStore",
    situation: str,
    limit: int = 3,
    namespace: str | None = None,
) -> list[dict]:
    """Retrieve relevant lessons for a situation. Filter by keyword overlap.
    namespace: when 'chat', only return lessons with session_type=='chat' (excludes test/autonomy).
    Skips retrieval for short social/introduction prompts to avoid contamination."""
    # Skip for social intros: "I am the person who built you", "Nice to meet you"
    q = situation.strip().lower()
    if len(q) < 60 and any(
        p in q for p in ("i am ", "i'm ", "nice to meet", "hello", "hi ", "hey ", "built you", "created you")
    ):
        return []
    words = [w for w in q.split() if len(w) > 1 and w not in _LESSON_STOPWORDS]
    if len(words) < 2:
        return []
    all_facts = memory.symbolic.get_all(kind="lesson")
    scored = []
    for f in all_facts:
        val = f.get("value")
        try:
            obj = json.loads(val) if isinstance(val, str) else val
            sit = obj.get("situation", "") if isinstance(obj, dict) else str(val)
            st = obj.get("session_type", "") if isinstance(obj, dict) else ""
        except (json.JSONDecodeError, TypeError):
            sit = str(val)
            st = ""
        # Namespace filter: chat only sees chat; autonomy sees chat+autonomy; test only test
        # Legacy (no session_type) excluded from namespace-filtered retrieval to avoid pollution
        if namespace == "chat":
            if st != "chat":
                continue
        elif namespace == "autonomy":
            if st and st not in ("chat", "autonomy"):
                continue
        elif namespace == "test":
            if st and st != "test":
                continue
        sit_lower = sit.lower()
        overlap = sum(1 for w in words if w in sit_lower)
        if overlap >= 2:  # Require at least 2 significant word overlaps
            scored.append((overlap, f))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:limit]]
