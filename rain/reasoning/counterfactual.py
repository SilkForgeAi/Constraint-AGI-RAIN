"""
Counterfactual reasoning — "what if X had been different?" (intervention vs observation).
Perfect reasoner pillar: causal simulation layer. Extends causal module.
"""

from __future__ import annotations


def needs_counterfactual(prompt: str) -> bool:
    """True if prompt asks for what-if or counterfactual reasoning."""
    lower = (prompt or "").lower()
    indicators = [
        "what if", "what would have", "suppose that", "if x had",
        "if we had", "if they had", "counterfactual", "had we",
        "would have been", "could have been", "alternate history",
        "if instead", "if not for", "without that",
    ]
    return any(i in lower for i in indicators)


def get_counterfactual_instruction() -> str:
    """Instruction for structured counterfactual output (actual vs counterfactual)."""
    return (
        "[Counterfactual reasoning: Structure your answer as (1) Actual: what did happen / what is the case; "
        "(2) Intervention: what we are changing (the counterfactual condition); "
        "(3) Counterfactual: what would have happened or would be the case under that change. "
        "Distinguish observation (what we see) from intervention (what we change).]"
    )
