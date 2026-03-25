"""
Tier 3: Abduction — best-explanation reasoning; hypothesis formation and selection.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

def abduce(engine: "CoreEngine", evidence: str, context: str = "", n_hypotheses: int = 3, max_tokens: int = 400) -> tuple[str, list[str]]:
    """Generate n_hypotheses explanations for the evidence; score and return best + alternatives."""
    if not (evidence or "").strip():
        return "", []
    prompt = f"Evidence or observation: {evidence[:400]}.\n\nList {n_hypotheses} possible explanations (hypotheses), one per line, numbered. Be concise."
    if context:
        prompt = f"Context: {context[:200]}\n\n" + prompt
    try:
        out = engine.complete(
            [{"role": "system", "content": "You propose hypotheses that best explain the evidence. One per line, numbered."},
             {"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=max_tokens)
        lines = [l.strip() for l in (out or "").strip().split("\n") if l.strip() and l[0:1].isdigit()]
        hypotheses = [l.split(".", 1)[-1].strip() for l in lines[:n_hypotheses] if len(l.split(".", 1)[-1].strip()) > 10]
        best = hypotheses[0] if hypotheses else ""
        return best, hypotheses[1:] if len(hypotheses) > 1 else []
    except Exception:
        return "", []
