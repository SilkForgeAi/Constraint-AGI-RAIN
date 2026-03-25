"""Multi-Agent Internal Cognition — competing reasoning paths with aggregation.

Multiple "perspectives" (e.g. skeptical, conservative, exploratory) each produce an answer;
aggregate by vote or by chair (one LLM call to select best). Single pipeline becomes
multi-view then merge. SAFETY: No self-set goals; used only for reasoning quality.
"""

from __future__ import annotations

import re
from typing import Any

PERSPECTIVES = [
    ("skeptical", "Question assumptions and consider counterarguments. Prefer minimal claims."),
    ("conservative", "Prefer safe, well-supported answers. Avoid speculation."),
    ("exploratory", "Consider multiple interpretations and edge cases."),
]


def _parse_json_list(raw: str) -> list[dict] | None:
    """Extract JSON list from model output."""
    raw = raw.strip()
    match = re.search(r"\[[\s\S]*\]", raw)
    if match:
        try:
            import json
            out = json.loads(match.group())
            if isinstance(out, list):
                return out
        except Exception:
            pass
    return None


def reason_multi_agent(
    question: str,
    engine: Any,
    context: str = "",
    n_agents: int = 3,
    aggregate: str = "vote",
    max_tokens_per_agent: int = 500,
) -> tuple[str, list[str]]:
    """
    Run n_agents perspectives (skeptical, conservative, exploratory), then aggregate.
    aggregate: "vote" = return majority or first on tie; "chair" = one LLM call to pick best.
    Returns (aggregated_answer, list of per-perspective answers).
    """
    n_agents = max(1, min(n_agents, len(PERSPECTIVES)))
    perspectives_to_use = PERSPECTIVES[:n_agents]
    answers: list[str] = []

    for name, instruction in perspectives_to_use:
        prompt = f"""Perspective: {name}.
Instruction: {instruction}

Question: {question}
{f'Context: {context}' if context else ''}

Answer concisely (one short paragraph or list). No preamble."""

        try:
            out = engine.complete(
                [
                    {"role": "system", "content": "You are a reasoning module. Answer only what is asked. Be concise."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=max_tokens_per_agent,
            ).strip()
            answers.append(out)
        except Exception:
            answers.append("")

    if not answers or all(not a for a in answers):
        return ("No consensus from multi-agent reasoning.", answers)

    if aggregate == "chair":
        # One LLM call: given question and the N answers, pick the best or synthesize.
        chair_prompt = f"""Question: {question}

The following answers were produced by different reasoning perspectives (skeptical, conservative, exploratory).
Pick the best answer or synthesize a single coherent answer that captures the strongest points. Output only the final answer, no meta-commentary."""

        for i, a in enumerate(answers, 1):
            chair_prompt += f"\n\n--- Answer {i} ---\n{a}"

        try:
            aggregated = engine.complete(
                [
                    {"role": "system", "content": "You are the chair. Output only the chosen or synthesized answer."},
                    {"role": "user", "content": chair_prompt},
                ],
                temperature=0.3,
                max_tokens=600,
            ).strip()
            return (aggregated, answers)
        except Exception:
            pass

    # Vote: for text we take the longest non-empty (heuristic for "most substantive") or first.
    non_empty = [a for a in answers if a.strip()]
    if not non_empty:
        return (answers[0] or "No answer.", answers)
    aggregated = max(non_empty, key=len)
    return (aggregated, answers)
