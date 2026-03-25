"""Generalization — schemas, analogy, few-shot from memory.

Mimics human ability to abstract patterns and apply to new situations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


def find_analogous(
    memory: "MemoryStore",
    situation: str,
    top_k: int = 3,
    namespace: str | None = None,
) -> list[dict]:
    """
    Find structurally similar past situations (analogical retrieval).
    Uses semantic search over experiences + lessons.
    namespace: filter to session_type (chat/autonomy/test).
    """
    similar = memory.recall_similar(situation, top_k=top_k, use_weighted=True, namespace=namespace)
    lessons = []
    try:
        from rain.learning.lessons import recall_lessons
        lessons = recall_lessons(memory, situation, limit=top_k, namespace=namespace)
    except Exception:
        pass
    out = []
    for s in similar:
        out.append({"type": "experience", "content": s.get("content", "")[:300], "source": "memory"})
    for lec in lessons:
        v = lec.get("value")
        if isinstance(v, str):
            try:
                import json
                v = json.loads(v)
            except Exception:
                v = {}
        if isinstance(v, dict):
            out.append({
                "type": "lesson",
                "situation": v.get("situation", "")[:150],
                "outcome": v.get("outcome", "")[:150],
                "source": "lesson",
            })
    return out[:top_k]


def format_few_shot_context(analogous: list[dict]) -> str:
    """Format analogous cases as few-shot examples for the LLM."""
    if not analogous:
        return ""
    lines = ["Similar past situations (use as reference for generalization):"]
    for i, a in enumerate(analogous, 1):
        if a.get("type") == "experience":
            lines.append(f"  {i}. {a.get('content', '')[:200]}")
        else:
            lines.append(f"  {i}. When: {a.get('situation','')[:100]} → Outcome: {a.get('outcome','')[:80]}")
    return "\n".join(lines)


def get_schema_hint(lessons: list) -> str:
    """Brief schema hint from lessons (abstract pattern)."""
    if not lessons:
        return ""
    # Simple heuristic: if multiple lessons share structure, note it
    return "Apply patterns from similar past situations when reasoning."
