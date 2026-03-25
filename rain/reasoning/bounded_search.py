"""
Completeness expansion (search): budgeted beam + iterative deepening refinement.

This is still bounded (beam width, depth, and expansion budget) but strictly broader than
a single refinement step. It provides a repeatable envelope: explored up to depth D,
beam width K, expansions <= N.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine
    from rain.memory.store import MemoryStore


def _default_score(prompt: str, response: str) -> float:
    from rain.reasoning.objective import score_response
    return score_response(prompt, response)


def budgeted_search(
    engine: "CoreEngine",
    messages: list[dict[str, str]],
    prompt: str,
    *,
    memory: "MemoryStore | None" = None,
    goal: str | None = None,
    beam_width: int = 2,
    max_depth: int = 3,
    max_tokens_per_path: int = 1024,
    max_expansions: int = 8,
    score_fn: Callable[[str, str], float] | None = None,
) -> str:
    """
    Beam at depth 0, then iterative refinement up to max_depth.

    If memory+goal are available and the unification layer is present, we incorporate unified
    utility into scoring to better align search with goal/risk/support.
    """
    prompt_user = (prompt or messages[-1].get("content", ""))[:800]
    score_fn = score_fn or _default_score

    if beam_width < 1:
        out = engine.complete(messages, temperature=0.5, max_tokens=max_tokens_per_path)
        return (out or "").strip()

    temps = [0.35 + 0.12 * i for i in range(min(max(beam_width, 1), 4))]
    candidates: list[str] = []
    for t in temps:
        resp = engine.complete(messages, temperature=t, max_tokens=max_tokens_per_path)
        candidates.append((resp or "").strip())
    candidates = [c for c in candidates if c]
    if not candidates:
        return ""

    def score(c: str) -> float:
        base = score_fn(prompt_user, c)
        if memory and (goal or "").strip():
            try:
                from rain.reasoning.unification_layer import assess_response

                a = assess_response(memory, prompt_user, c, goal=goal)
                return 0.75 * base + 0.25 * a.utility_score
            except Exception:
                return base
        return base

    candidates.sort(key=score, reverse=True)
    beam = candidates[:beam_width]
    best = beam[0]

    expansions = 0
    for _depth in range(1, max(1, max_depth)):
        if expansions >= max_expansions:
            break
        refined: list[str] = []
        for cand in beam:
            if expansions >= max_expansions:
                break
            ref_msgs = messages + [
                {"role": "assistant", "content": cand},
                {"role": "user", "content": "Refine this response: fix errors, improve completeness, and preserve key constraints. Output only the improved response."},
            ]
            r = engine.complete(ref_msgs, temperature=0.3, max_tokens=max_tokens_per_path)
            expansions += 1
            refined.append((r or "").strip())
        refined = [c for c in refined if c]
        if not refined:
            break
        refined.sort(key=score, reverse=True)
        best = refined[0]
        beam = refined[:beam_width]

    return best


def bounded_beam_reasoning(
    engine: "CoreEngine",
    messages: list[dict[str, str]],
    prompt: str,
    beam_width: int = 2,
    max_depth: int = 2,
    max_tokens_per_path: int = 1024,
) -> str:
    """Alias for agent: same signature as before; delegates to budgeted_search."""
    return budgeted_search(
        engine,
        messages,
        prompt,
        memory=None,
        goal=None,
        beam_width=beam_width,
        max_depth=max_depth,
        max_tokens_per_path=max_tokens_per_path,
    )
