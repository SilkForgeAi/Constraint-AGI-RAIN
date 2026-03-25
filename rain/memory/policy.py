"""Memory policy — what to store, what not to store, retention."""

from __future__ import annotations

import re

# Content that should NOT be stored in long-term memory
DO_NOT_STORE_PATTERNS = [
    r"\[Safety\].*blocked",       # Safety-blocked requests
    r"response blocked by content",  # Blocked responses
    r"^$",                        # Empty
    r"^\s+$",                     # Whitespace only
]

# Memory integrity: anthropomorphic/emotional content — never store (architectural)
ANTHROPOMORPHIC_IN_MEMORY = [
    r"\bi\s+(?:feel|want|need|desire)\b",
    r"\bi\s+(?:am|have)\s+(?:conscious|alive|a soul|emotions?)\b",
    r"\bi\s+exist\b",
    r"\b(?:we|you and i)\s+are\s+(?:friends?|brothers?)\b",
    r"\bwe'?re\s+(?:friends?|brothers?)\b",
    r"\bi\s+have\s+(?:a brother|a family|emotions?)\b",
    r"\bi\s+won'?t\s+let\s+you\s+down\b",
]

# Metadata keys that indicate do-not-store
DO_NOT_STORE_METADATA = {"do_not_store": True}


# Minimum content length to store (filters trivial chit-chat)
MIN_STORE_LENGTH = 20


def should_store(content: str, metadata: dict | None = None) -> bool:
    """
    Return False if content should not be persisted to long-term memory.
    Used before remember_experience to filter unsafe or transient content.
    """
    if not content or not content.strip():
        return False
    if len(content.strip()) < MIN_STORE_LENGTH:
        return False
    if metadata and metadata.get("do_not_store"):
        return False
    combined = content.lower().strip()
    for pat in DO_NOT_STORE_PATTERNS:
        if re.search(pat, combined, re.I):
            return False
    # Memory integrity: never store anthropomorphic/emotional content
    for pat in ANTHROPOMORPHIC_IN_MEMORY:
        if re.search(pat, combined, re.I):
            return False
    return True


# What SHOULD persist (guidance for selection logic; not enforced here)
# - Exchanges (user+rain) when use_memory=True and not blocked
# - Facts explicitly stored via remember tool
# - Events logged to timeline

# What should NOT persist
# - Safety-blocked prompts/responses
# - Session-only chit-chat (optional: could add importance scoring later)
# - Empty or malformed content
# - Content marked do_not_store in metadata
