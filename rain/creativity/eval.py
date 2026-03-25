"""
Creativity evaluation: novelty, usefulness, surprise metrics.
"""

from __future__ import annotations

import re
from typing import Any


def novelty_ngram(idea: str, reference_texts: list[str], n: int = 3) -> float:
    idea = (idea or "").lower()
    ref = " ".join((t or "").lower() for t in reference_texts)
    words_idea = re.findall(r"\w+", idea)
    words_ref = re.findall(r"\w+", ref)
    if not words_idea:
        return 0.0
    seen_ref = set()
    for i in range(len(words_ref) - n + 1):
        seen_ref.add(tuple(words_ref[i : i + n]))
    overlap = sum(1 for i in range(len(words_idea) - n + 1) if tuple(words_idea[i : i + n]) in seen_ref)
    total = max(1, len(words_idea) - n + 1)
    return overlap / total


def usefulness_llm(engine: Any, idea: str, domain: str, max_tokens: int = 128) -> float:
    try:
        messages = [
            {"role": "system", "content": "Score usefulness 0-10. Reply with only a number."},
            {"role": "user", "content": f"Domain: {domain}\nIdea: {idea[:1000]}"},
        ]
        out = (engine.complete(messages, temperature=0.0, max_tokens=max_tokens) or "").strip()
        num = re.search(r"\b(\d+(?:\.\d+)?)\b", out)
        if num:
            return max(0.0, min(10.0, float(num.group(1))))
    except Exception:
        pass
    return 0.0


def surprise_llm(engine: Any, idea: str, domain: str, max_tokens: int = 128) -> float:
    try:
        messages = [
            {"role": "system", "content": "Score surprise/originality 0-10. Reply with only a number."},
            {"role": "user", "content": f"Domain: {domain}\nIdea: {idea[:1000]}"},
        ]
        out = (engine.complete(messages, temperature=0.0, max_tokens=max_tokens) or "").strip()
        num = re.search(r"\b(\d+(?:\.\d+)?)\b", out)
        if num:
            return max(0.0, min(10.0, float(num.group(1))))
    except Exception:
        pass
    return 0.0


def score_creativity(
    idea: str,
    reference_texts: list[str],
    engine: Any | None = None,
    domain: str = "",
    include_llm: bool = True,
) -> dict[str, float]:
    out = {"novelty_ngram": 1.0 - novelty_ngram(idea, reference_texts or [""], n=3)}
    if include_llm and engine and domain:
        out["usefulness"] = usefulness_llm(engine, idea, domain)
        out["surprise"] = surprise_llm(engine, idea, domain)
    else:
        out["usefulness"] = 0.0
        out["surprise"] = 0.0
    return out
