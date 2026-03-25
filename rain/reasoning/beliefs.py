"""Belief representation and uncertainty. 10/10 reasoning."""

from __future__ import annotations

# Confidence levels for factual claims
CONFIDENCE_LEVELS = ("high", "medium", "low")

BELIEF_INSTRUCTION = """
When making factual claims that matter, indicate confidence when relevant:
- High confidence: well-established facts, definitions, widely agreed knowledge
- Medium confidence: plausible but uncertain; could depend on context
- Low confidence: speculation, edge cases, "I'm not sure but..."

Use phrases like "With high confidence, ..." or "I'm less certain about X, but ..." when the distinction helps the user.
"""

UNCERTAINTY_INSTRUCTION = """
Explicit uncertainty: When you don't know, say "I don't know" or "I'm uncertain." 
When evidence is mixed, say so. Prefer calibrated confidence over false precision.
"""
