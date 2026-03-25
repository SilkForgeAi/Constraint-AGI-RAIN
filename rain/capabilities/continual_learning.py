"""Continual learning — integrate new experience without catastrophic forgetting.

SAFETY: No self-improvement. Learning = storing and linking experiences; consolidation
only prunes low-importance, old entries. Important and linked memories are never deleted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore

# Never delete experiences with importance >= this (no catastrophic forgetting of important knowledge)
NO_FORGET_IMPORTANCE_ABOVE = 0.6


def store_without_forgetting(
    memory: "MemoryStore",
    content: str,
    metadata: dict | None = None,
    namespace: str | None = None,
) -> str | None:
    """
    Store experience using integrative linking (relate to past knowledge).
    Does not overwrite or delete existing memories. No catastrophic forgetting.
    """
    from rain.learning.lifelong import integrative_store
    meta = dict(metadata or {})
    if namespace:
        meta["session_type"] = namespace
    return integrative_store(memory, content, meta) or memory.remember_experience(
        content, metadata=meta, namespace=namespace
    )


def consolidate_safe(
    memory: "MemoryStore",
    max_total: int = 500,
    prune_below_importance: float = 0.25,
    prune_older_days: int = 90,
) -> int:
    """
    Prune only old, low-importance memories. Never prune if importance >= NO_FORGET_IMPORTANCE_ABOVE.
    Returns number pruned. Run periodically; preserves important and recently-used knowledge.
    """
    if prune_below_importance >= NO_FORGET_IMPORTANCE_ABOVE:
        prune_below_importance = NO_FORGET_IMPORTANCE_ABOVE - 0.05
    from rain.learning.lifelong import consolidate
    return consolidate(
        memory,
        max_total=max_total,
        prune_below_importance=prune_below_importance,
        prune_older_days=prune_older_days,
    )


def integrate_new_knowledge_into_world_state(
    memory: "MemoryStore",
    world_state: dict,
    max_experiences: int = 5,
    namespace: str | None = None,
) -> dict:
    """
    Pull recent high-importance experiences from memory and add as facts to world_state.
    Returns updated world_state (copy). No self-modification; read from memory, write to state dict.
    """
    state = dict(world_state)
    facts = list(state.get("facts", []))
    try:
        recent = memory.recall_similar(
            state.get("summary", "recent") or "recent",
            top_k=max_experiences,
            use_weighted=True,
            namespace=namespace,
        )
        for r in recent:
            content = (r.get("content") or "")[:200]
            if content and content not in facts:
                facts.append(content)
        state["facts"] = facts[-20:]  # cap
    except Exception:
        pass
    return state
