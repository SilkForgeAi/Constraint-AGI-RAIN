"""
Tier 3: Memory integration — store reasoning outcomes for long-horizon context.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rain.memory.store import MemoryStore

def store_reasoning_outcome(memory: "MemoryStore", prompt: str, response: str, namespace: str | None = None) -> None:
    """Extract one or two key facts from the response and store for future retrieval."""
    if not (response or "").strip():
        return
    r = (response or "").strip()
    sentences = [s.strip() for s in r.split(". ") if 15 <= len(s.strip()) <= 120][:2]
    for s in sentences:
        if s and not any(x in s.lower() for x in ("i think", "perhaps", "maybe")):
            try:
                memory.remember_fact("reasoning_" + str(hash(s) % 10**10), {"fact": s, "prompt_preview": prompt[:100]}, kind="reasoning")
            except Exception:
                pass
