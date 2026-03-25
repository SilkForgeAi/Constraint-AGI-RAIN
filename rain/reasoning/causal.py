"""Causal inference — structured cause-effect reasoning.

Epistemic humility: outputs are "likely" not "certain". Confidence indicated.
"""

from __future__ import annotations

from rain.core.engine import CoreEngine


CAUSAL_PROMPT = """You are analyzing cause-effect relationships.
- Distinguish correlation from causation
- Indicate confidence (high/medium/low)
- When uncertain, say so
- Output structured: cause, effect, confidence, mechanism (brief)
- Avoid false precision"""


class CausalInference:
    """Structured cause-effect reasoning. Epistemically humble."""

    def __init__(self, engine: CoreEngine | None = None):
        self.engine = engine or CoreEngine()

    def infer_causes(self, effect: str, candidates: str = "", context: str = "") -> str:
        """Given an effect, reason about likely causes. Returns structured analysis."""
        prompt = f"""Effect/observation: {effect}
{f'Candidate causes to consider: {candidates}' if candidates else ''}
{f'Context: {context}' if context else ''}

What are the likely causes? For each, note confidence and mechanism."""
        return self.engine.complete(
            [
                {"role": "system", "content": CAUSAL_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        ).strip()

    def predict_effects(self, cause: str, context: str = "") -> str:
        """Given a cause, reason about likely effects. Returns structured analysis."""
        prompt = f"""Cause/action: {cause}
{f'Context: {context}' if context else ''}

What are the likely effects? For each, note confidence."""
        return self.engine.complete(
            [
                {"role": "system", "content": CAUSAL_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        ).strip()
