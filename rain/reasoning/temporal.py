"""
Tier 3: Temporal — time-aware state and labels.
"""
from __future__ import annotations
from datetime import datetime

def temporal_reasoning_instruction() -> str:
    """Instruction for time-aware reasoning (order, recency)."""
    return "When reasoning about events or facts, respect order and recency; earlier events can cause later ones, not the reverse."

def with_timestamp(summary: str, turn_id: int | None = None) -> str:
    """Prepend a when label to a summary."""
    when = datetime.utcnow().strftime("%Y-%m-%d %H:%M") if turn_id is None else f"turn_{turn_id}"
    return f"[As of {when}] {summary}"
