"""
Session world state — Tier 2: consistency/state across turns.

Maintains a compact, consistent state (facts/beliefs) per session. Updated after each turn;
checked for contradiction; summary injected into next prompt so reasoning is not stateless.

SAFETY: Session-bound only. No persistence across sessions. No self-set state.
"""

from __future__ import annotations

import re
from typing import Any

MAX_FACTS = 24
MAX_SUMMARY_CHARS = 600

def _simple_negation(a: str, b: str) -> bool:
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b or a == b:
        return False
    if (" not " in a or " never " in a or " no " in a) != (" not " in b or " never " in b or " no " in b):
        core_a = re.sub(r"[^a-z0-9]", "", a[:40])
        core_b = re.sub(r"[^a-z0-9]", "", b[:40])
        if len(core_a) > 8 and len(core_b) > 8 and (core_a in core_b or core_b in core_a):
            return True
    return False

class SessionWorldState:
    def __init__(self, max_facts: int = MAX_FACTS) -> None:
        self._facts: list[str] = []
        self._max_facts = max(max_facts, 4)
        self._last_conflict: str = ""

    def get_state(self) -> dict[str, Any]:
        return {"facts": list(self._facts), "last_conflict": self._last_conflict}

    def update_from_turn(self, prompt: str, response: str) -> None:
        if not (response or "").strip():
            return
        r = (response or "").strip()
        sentences = re.findall(r"[A-Z][^.!?]*[.!?]", r)
        added = 0
        for s in sentences:
            s = s.strip()
            if 10 <= len(s) <= 180 and s not in self._facts:
                if any(w in s.lower() for w in ("i think", "i believe", "perhaps", "maybe", "could be")):
                    continue
                self._facts.append(s)
                added += 1
                if len(self._facts) > self._max_facts:
                    self._facts.pop(0)
                if added >= 3:
                    break

    def check_consistency(self) -> tuple[bool, str]:
        self._last_conflict = ""
        for i, a in enumerate(self._facts):
            for j, b in enumerate(self._facts):
                if i >= j:
                    continue
                if _simple_negation(a, b):
                    self._last_conflict = f"Conflict: {a[:60]} vs {b[:60]}"
                    return False, self._last_conflict
        return True, "ok"

    def get_summary_for_prompt(self) -> str:
        if not self._facts:
            return ""
        lines = ["Session state (consistent facts so far):"]
        for f in self._facts[-8:]:
            lines.append(f"- {f[:120]}{'...' if len(f) > 120 else ''}")
        out = "\n".join(lines)
        return out[:MAX_SUMMARY_CHARS] + ("..." if len(out) > MAX_SUMMARY_CHARS else "")

    def clear(self) -> None:
        self._facts.clear()
        self._last_conflict = ""
