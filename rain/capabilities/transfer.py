"""Transfer and composition — reuse skills and concepts from other domains.

SAFETY: Read-only retrieval. No execution. Injects hints into planning context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


def get_transfer_hint(
    memory: "MemoryStore",
    goal: str,
    top_k: int = 3,
    namespace: str | None = "autonomy",
) -> str:
    """
    Retrieve analogous past situations and lessons from memory (possibly other domains).
    Returns formatted string for planner context. Transfer = reuse patterns elsewhere.
    """
    from rain.learning.generalization import find_analogous, format_few_shot_context
    analogous = find_analogous(memory, goal, top_k=top_k, namespace=namespace)
    return format_few_shot_context(analogous)


def compose_skills(
    memory: "MemoryStore",
    goal: str,
    top_k: int = 5,
    namespace: str | None = "autonomy",
) -> list[dict[str, Any]]:
    """
    Suggest a composition of skills from memory relevant to goal (cross-domain).
    Returns list of {type, content/situation, outcome} for planner to consider.
    """
    from rain.learning.generalization import find_analogous
    analogous = find_analogous(memory, goal, top_k=top_k, namespace=namespace)
    out: list[dict[str, Any]] = []
    for a in analogous:
        if a.get("type") == "experience":
            out.append({"type": "experience", "content": a.get("content", "")[:300]})
        else:
            out.append({
                "type": "lesson",
                "situation": a.get("situation", "")[:200],
                "outcome": a.get("outcome", "")[:200],
            })
    return out
