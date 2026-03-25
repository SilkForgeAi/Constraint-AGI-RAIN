"""Contradiction detection — avoid storing conflicting memories."""

from __future__ import annotations

# Negation/opposition keywords — when both appear in similar content, potential conflict
CONTRADICTION_SIGNALS = [
    ("is", "is not"),
    ("is not", "is"),
    ("always", "never"),
    ("never", "always"),
    ("true", "false"),
    ("false", "true"),
    ("yes", "no"),
    ("no", "yes"),
    ("agree", "disagree"),
    ("correct", "incorrect"),
    ("wrong", "right"),
]


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def might_contradict(new_content: str, existing_content: str) -> bool:
    """
    Heuristic: do these two texts potentially contradict each other?
    Fast check; no LLM. Returns True if we should be cautious.
    """
    a = _normalize(new_content)
    b = _normalize(existing_content)
    if len(a) < 30 or len(b) < 30:
        return False
    # Same topic (word overlap)
    words_a = set(a.split())
    words_b = set(b.split())
    overlap = len(words_a & words_b) / max(1, len(words_a | words_b))
    if overlap < 0.2:
        return False  # Different topics
    # Check for opposition pairs
    for neg, pos in CONTRADICTION_SIGNALS:
        if (neg in a and pos in b) or (pos in a and neg in b):
            return True
    return False


def filter_contradicting(
    new_content: str, candidates: list[dict], threshold: bool = True
) -> list[dict]:
    """
    From candidates (each has 'content' key), return those that might contradict new_content.
    If threshold: only return if we have high-similarity candidates (by distance).
    """
    contradicting = []
    for c in candidates:
        content = c.get("content", "")
        dist = c.get("distance", 1.0)
        # Only consider similar content (cosine distance < 0.5 = fairly similar)
        if threshold and dist > 0.5:
            continue
        if might_contradict(new_content, content):
            contradicting.append(c)
    return contradicting
