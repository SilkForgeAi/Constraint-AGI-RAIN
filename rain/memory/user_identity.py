"""User identity — who the primary user is. Always remembered across sessions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore

USER_IDENTITY_KEY = "user_identity"


def _extract_name_from_text(text: str) -> str | None:
    """Extract a name from self-identification phrases."""
    text = text.strip()
    if len(text) < 3:
        return None
    # "I'm Aaron", "I am Aaron", "My name is Aaron", "Call me Aaron", "This is Aaron"
    patterns = [
        r"(?:i'?m|i am)\s+([A-Za-z][A-Za-z0-9_-]{0,30})\b",
        r"(?:my name is|call me|this is)\s+([A-Za-z][A-Za-z0-9_\s-]{0,30})\b",
        r"(?:name'?s|named)\s+([A-Za-z][A-Za-z0-9_-]{0,30})\b",
        r"^([A-Za-z][A-Za-z0-9_-]{1,30})\s*(?:here|speaking)?$",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            name = m.group(1).strip()
            if len(name) >= 2 and name.lower() not in ("i", "me", "my", "the", "a", "an"):
                return name
    return None


def store_user_identity(memory: "MemoryStore", name: str, facts: list[str] | None = None) -> None:
    """Store who the user is. Overwrites existing."""
    value = {"name": name.strip()[:100], "facts": list(facts or [])[:20]}
    memory.remember_fact(USER_IDENTITY_KEY, value, kind="user_identity")


def add_user_fact(memory: "MemoryStore", fact: str) -> None:
    """Add a fact about the user. Appends to existing identity."""
    existing = recall_user_identity(memory)
    facts = list(existing.get("facts", []))
    if fact.strip() and fact.strip()[:200] not in facts:
        facts.append(fact.strip()[:200])
    name = existing.get("name", "User")
    store_user_identity(memory, name, facts[-20:])


def recall_user_identity(memory: "MemoryStore") -> dict:
    """Get stored user identity. Returns {name, facts} or empty dict."""
    val = memory.recall_fact(USER_IDENTITY_KEY, kind="user_identity")
    if val and isinstance(val, dict):
        return {"name": val.get("name", ""), "facts": val.get("facts", [])}
    return {"name": "", "facts": []}


def extract_and_store_from_message(memory: "MemoryStore", user_message: str) -> bool:
    """
    If user_message contains self-identification, extract and store. Returns True if updated.
    """
    name = _extract_name_from_text(user_message)
    if not name:
        return False
    store_user_identity(memory, name)
    return True


def format_user_identity_context(identity: dict) -> str:
    """Format for injection into prompt context."""
    if not identity or not identity.get("name"):
        return ""
    parts = [f"The user's name is {identity['name']}."]
    facts = identity.get("facts", [])
    if facts:
        for f in facts[:5]:
            parts.append(f"  - {f}")
    return "Remember: " + " ".join(parts)
