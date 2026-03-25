"""General reasoning — analogy, counterfactual, explain in novel domains.

SAFETY: Reasoning only. No execution. No self-modification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine


def reason_analogy(
    engine: "CoreEngine",
    situation: str,
    analogous_examples: str,
    query: str = "",
) -> str:
    """Reason by analogy: given situation and similar past cases, draw a conclusion."""
    prompt = f"""Situation: {situation}
{analogous_examples}
{f'Query: {query}' if query else 'What is the most plausible conclusion or next step?'}
Reason by analogy. Be concise. If uncertain, say so."""
    out = engine.complete(
        [
            {"role": "system", "content": "You reason by analogy. Stay grounded. No fabrication."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=400,
    )
    return out.strip()


def reason_counterfactual(
    engine: "CoreEngine",
    state_or_fact: str,
    what_if: str,
) -> str:
    """Counterfactual: what would follow if something were different?"""
    prompt = f"""Current state/fact: {state_or_fact}
What if: {what_if}
What would likely follow? One short paragraph. Use "would", "might", "could". If very uncertain, say so."""
    out = engine.complete(
        [
            {"role": "system", "content": "You reason about counterfactuals. Stay grounded."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return out.strip()


def reason_explain(
    engine: "CoreEngine",
    claim_or_outcome: str,
    context: str = "",
) -> str:
    """Explain why something might be so; robust chain of inference."""
    prompt = f"""Claim/outcome: {claim_or_outcome}
{f'Context: {context}' if context else ''}
Explain briefly why this might be so. Give a short chain of reasoning. If uncertain, say so."""
    out = engine.complete(
        [
            {"role": "system", "content": "You explain with clear reasoning. No fabrication."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=400,
    )
    return out.strip()
