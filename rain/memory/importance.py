"""Importance scoring — what to store, what to prioritize in retrieval."""

from __future__ import annotations

import re
from datetime import datetime

# Heuristic signals for importance (no LLM call — fast)
SUBSTANTIVE_PATTERNS = [
    r"\b(?:why|how|what|when|where|who|explain|describe|define)\b",
    r"\b(?:because|therefore|however|although)\b",
    r"\d+",  # Numbers often indicate concrete facts
    r"\b(?:remember|important|key|critical|note)\b",
    r"[.!?]$",  # Complete thought
]

CHIT_CHAT_PATTERNS = [
    r"^(?:hi|hey|hello|bye|ok|yes|no|lol|haha)\b",
    r"^(?:thanks|thank you|cool|nice|great)\s*[.!]?$",
]


def score_importance(content: str, metadata: dict | None = None) -> float:
    """
    Score 0.0–1.0 how worth storing/prioritizing this content is.
    Heuristic-based; no LLM. Higher = more substantive.
    """
    if not content or len(content.strip()) < 20:
        return 0.0
    if metadata and metadata.get("type") == "skill":
        return 0.95  # Procedural knowledge is high value
    if metadata and metadata.get("type") == "fact":
        return 0.9

    text = content.strip().lower()
    score = 0.3  # Base

    # Length bonus (diminishing)
    length = len(text)
    if length > 100:
        score += 0.15
    if length > 300:
        score += 0.1
    if length > 500:
        score += 0.05

    # Substantive signals
    for pat in SUBSTANTIVE_PATTERNS:
        if re.search(pat, text, re.I):
            score += 0.08
            break

    # Chit-chat penalty
    for pat in CHIT_CHAT_PATTERNS:
        if re.search(pat, text, re.I):
            score -= 0.2
            break

    return min(1.0, max(0.0, score))
