"""Lifelong learning — consolidation, integrative storage, forgetting curve.

Mimics human continuous learning: link new to old, consolidate, prune redundancy.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.memory.store import MemoryStore


def integrative_store(
    memory: "MemoryStore",
    content: str,
    metadata: dict | None = None,
) -> str | None:
    """
    Store experience while linking to related past knowledge (integrative learning).
    Finds similar experiences and adds relates_to in metadata for retrieval graphs.
    """
    # Retrieve similar before store
    similar = memory.vector.search(content, top_k=3)
    meta = dict(metadata or {})
    if similar:
        related_ids = [s.get("id", "") for s in similar if s.get("id")]
        if related_ids:
            meta["relates_to"] = ",".join(related_ids[:5])  # ChromaDB: str only
    return memory.remember_experience(content, meta)


def consolidate(
    memory: "MemoryStore",
    max_total: int = 500,
    prune_below_importance: float = 0.25,
    prune_older_days: int = 90,
) -> int:
    """
    Prune redundant or very old low-importance memories. Prevents unbounded growth.
    Returns number of memories pruned. Run periodically (e.g. weekly).
    """
    try:
        items = memory.vector.get_all_metadata()
    except Exception:
        return 0
    ids = [i[0] for i in items]
    metadatas = [i[1] for i in items]
    if len(ids) <= max_total:
        return 0

    now = datetime.now()
    to_prune = []
    for i, (vid, meta) in enumerate(zip(ids, metadatas)):
        if len(ids) - len(to_prune) <= max_total:
            break
        imp = float(meta.get("importance", 0.5))
        ts = meta.get("timestamp", "")[:10]
        if imp < prune_below_importance and ts:
            try:
                stored = datetime.strptime(ts, "%Y-%m-%d").date()
                delta = (now.date() - stored).days
                if delta > prune_older_days:
                    to_prune.append(vid)
            except Exception:
                pass

    for vid in to_prune[:100]:  # Cap per run
        memory.forget_experience(vid)
    return len(to_prune)


def get_decayed_recency_weight(timestamp_str: str, half_life_days: float = 14) -> float:
    """
    Forgetting curve: older memories contribute less. Returns 0-1.
    half_life_days: days until recency weight halves.
    """
    if not timestamp_str:
        return 0.5
    try:
        ts = timestamp_str[:10]
        stored = datetime.strptime(ts, "%Y-%m-%d").date()
        delta = (datetime.now().date() - stored).days
        import math
        return 0.5 ** (max(0, delta) / half_life_days)
    except Exception:
        return 0.5
