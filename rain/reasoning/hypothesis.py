"""
Hypothesis generation — generate, evaluate, and rank competing hypotheses for complex prompts.

For analytical, explanatory, or design prompts, Rain generates 2-3 competing hypotheses,
evaluates each against known context, and selects the most defensible one. The answer
carries falsification conditions — making it more confident and auditable.

Called from _run_reasoning() before the final LLM call on analytical/deep-reasoning prompts.
Injects the best hypothesis + its support into the user content so the LLM builds on it.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

N_HYPOTHESES_DEFAULT = 3

_HYPOTHESIS_TRIGGERS = (
    r"\bwhy\b",
    r"\bexplain\b",
    r"\bwhat\s+cause",
    r"\bhow\s+does\b",
    r"\bhow\s+would\b",
    r"\bdesign\b",
    r"\barchitect",
    r"\bpropose\b",
    r"\btheor",
    r"\bhypothes",
    r"\bwhat\s+is\s+the\s+best\b",
    r"\boptimal\b",
    r"\bstrateg",
    r"\banalyze\b",
    r"\bassess\b",
    r"\bevaluat",
    r"\bwhat\s+would\s+happen",
    r"\bpredict\b",
    r"\bcompare\b",
)


def is_hypothesis_worthy(prompt: str) -> bool:
    """True when the prompt is analytical enough to benefit from hypothesis generation."""
    p = (prompt or "").lower()
    return any(re.search(t, p) for t in _HYPOTHESIS_TRIGGERS)


def generate_hypotheses(
    engine: "CoreEngine",
    prompt: str,
    context: str = "",
    n: int = N_HYPOTHESES_DEFAULT,
) -> list[dict]:
    """
    Generate n competing hypotheses for the given prompt.

    Returns list of dicts:
      {hypothesis, support, falsification, confidence, score}
    sorted by score descending.
    """
    n = max(2, min(4, n))
    ctx_block = f"\nContext:\n{context[:600]}" if context else ""
    gen_prompt = (
        f"You are a rigorous analytical reasoner.\n\n"
        f"Given this question/task:{ctx_block}\n\n"
        f"Question: {prompt[:400]}\n\n"
        f"Generate exactly {n} competing hypotheses or approaches. For each:\n"
        f"1. State the hypothesis clearly (1-2 sentences)\n"
        f"2. Give the strongest supporting evidence/reasoning (1-2 sentences)\n"
        f"3. State one condition that would falsify or disprove it (1 sentence)\n"
        f"4. Rate your confidence: high / medium / low\n\n"
        f"Format each as:\n"
        f"H[N]: <hypothesis>\n"
        f"Support: <evidence>\n"
        f"Falsification: <condition>\n"
        f"Confidence: <high|medium|low>\n\n"
        f"Output nothing else."
    )
    try:
        msgs = [{"role": "user", "content": gen_prompt}]
        raw = engine.complete(msgs, temperature=0.6, max_tokens=900)
    except Exception:
        return []
    return _parse_hypotheses(raw or "")


def _parse_hypotheses(text: str) -> list[dict]:
    """Parse structured hypothesis output into dicts."""
    blocks = re.split(r"\nH\d+:", "\n" + text)
    conf_score = {"high": 0.9, "medium": 0.6, "low": 0.3}
    results: list[dict] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        hypothesis = lines[0].strip() if lines else ""
        support = ""
        falsification = ""
        confidence = "medium"
        for line in lines[1:]:
            ll = line.strip()
            if ll.lower().startswith("support:"):
                support = ll[8:].strip()
            elif ll.lower().startswith("falsification:"):
                falsification = ll[14:].strip()
            elif ll.lower().startswith("confidence:"):
                c = ll[11:].strip().lower()
                if c in conf_score:
                    confidence = c
        if hypothesis:
            results.append({
                "hypothesis": hypothesis[:300],
                "support": support[:300],
                "falsification": falsification[:200],
                "confidence": confidence,
                "score": conf_score.get(confidence, 0.6),
            })
    results.sort(key=lambda h: -h["score"])
    return results


def select_best_hypothesis(hypotheses: list[dict]) -> dict | None:
    """Return the highest-scored hypothesis, or None if empty."""
    return hypotheses[0] if hypotheses else None


def format_hypotheses_for_context(hypotheses: list[dict], best_only: bool = False) -> str:
    """Format hypotheses as a compact context block for injection into reasoning."""
    if not hypotheses:
        return ""
    if best_only or len(hypotheses) == 1:
        h = hypotheses[0]
        return (
            f"[Best hypothesis ({h['confidence']} confidence): {h['hypothesis']} "
            f"| Support: {h['support']} "
            f"| Falsified if: {h['falsification']}]"
        )
    lines = ["[Competing hypotheses — ranked by confidence:"]
    for i, h in enumerate(hypotheses[:3], 1):
        lines.append(
            f"  H{i} ({h['confidence']}): {h['hypothesis']}"
            + (f" — Support: {h['support']}" if h["support"] else "")
        )
    lines.append(
        "Select the most defensible hypothesis and build your answer from it. "
        "State which you chose and why the others were ruled out.]"
    )
    return "\n".join(lines)
