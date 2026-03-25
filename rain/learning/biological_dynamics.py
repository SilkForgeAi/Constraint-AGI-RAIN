"""Biological-Style Learning Dynamics — consolidation phases, importance-based pruning, replay.

Consolidation phase: run consolidate_safe (no-forgetting policy); prune only old low-importance.
Replay phase: re-retrieve top-k high-importance experiences to reinforce retrieval order (no weight updates).
Sleep phase: run consolidation + optional replay; call after N interactions or on schedule.
SAFETY: No self-improvement. No model/weight updates. Memory only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore

from rain.capabilities.continual_learning import consolidate_safe, NO_FORGET_IMPORTANCE_ABOVE


def consolidation_phase(
    memory: "MemoryStore",
    max_total: int = 500,
    prune_below_importance: float = 0.25,
    prune_older_days: int = 90,
) -> int:
    """
    Run safe consolidation: prune only old, low-importance memories.
    Never prunes above NO_FORGET_IMPORTANCE_ABOVE. Returns number pruned.
    """
    if prune_below_importance >= NO_FORGET_IMPORTANCE_ABOVE:
        prune_below_importance = NO_FORGET_IMPORTANCE_ABOVE - 0.05
    return consolidate_safe(
        memory,
        max_total=max_total,
        prune_below_importance=prune_below_importance,
        prune_older_days=prune_older_days,
    )


def replay_phase(
    memory: "MemoryStore",
    query: str = "recent experiences and key facts",
    top_k: int = 20,
    namespace: str | None = None,
) -> list[dict]:
    """
    Re-retrieve top-k high-importance experiences. Does not change embeddings or weights.
    "Replay" in the biological sense: reinforce retrieval paths by re-accessing important memories.
    Returns list of recalled items (for logging or downstream use).
    """
    try:
        return memory.recall_similar(
            query,
            top_k=top_k,
            use_weighted=True,
            namespace=namespace,
        )
    except Exception:
        return []


def sleep_phase(
    memory: "MemoryStore",
    max_total: int = 500,
    prune_below_importance: float = 0.25,
    prune_older_days: int = 90,
    run_replay: bool = True,
    replay_top_k: int = 15,
) -> dict:
    """
    Full "sleep" phase: consolidation (prune old low-importance) then optional replay.
    Returns {"pruned": N, "replay_count": M}. No model/weight updates.
    """
    pruned = consolidation_phase(
        memory,
        max_total=max_total,
        prune_below_importance=prune_below_importance,
        prune_older_days=prune_older_days,
    )
    replay_count = 0
    if run_replay:
        replayed = replay_phase(memory, top_k=replay_top_k, namespace=None)
        replay_count = len(replayed)
    return {"pruned": pruned, "replay_count": replay_count}
