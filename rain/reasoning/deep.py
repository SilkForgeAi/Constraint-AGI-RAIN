"""
Deeper reasoning: multi-path (tree-of-thought style). Generate several candidate answers, then pick the best.

SAFETY: Reasoning only. No execution. All candidates and referee use same engine; safety checks apply to final output in agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

from rain.config import METACOG_ENABLED


def multi_path_reasoning(
    engine: "CoreEngine",
    messages: list[dict[str, str]],
    num_paths: int = 2,
    max_tokens_per_path: int = 1024,
    prompt: str | None = None,
    constraints: list[str] | None = None,
    goal: str | None = None,
    metacog_top_k: int = 2,
) -> str:
    """
    Minimal “most wins” selection:
    1) constraint-first filtering (keep all valid candidates)
    2) objective scoring (rank candidates)
    3) bounded metacog self-check on top-K tie-break
    4) LLM referee only as a last resort (top-2)
    """

    if num_paths < 2:
        out = engine.complete(messages, temperature=0.5, max_tokens=max_tokens_per_path)
        return (out or "").strip()

    # Temperature schedule: small spread so candidates differ without collapsing quality.
    temps = [0.4, 0.6, 0.5][:num_paths] if num_paths <= 3 else [0.4 + 0.1 * i for i in range(num_paths)]

    candidates: list[str] = []
    for t in temps:
        resp = engine.complete(messages, temperature=t, max_tokens=max_tokens_per_path)
        candidates.append((resp or "").strip())

    candidates = [c for c in candidates if c]
    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]

    prompt_user = (prompt or messages[-1].get("content", "")).strip()[:800]

    # Tier 1: constraint-first — keep only candidates that satisfy all constraints
    if constraints:
        try:
            from rain.reasoning.constraint_first import filter_valid_candidates, NO_VALID_MESSAGE

            valid = filter_valid_candidates(candidates, constraints)
            if not valid:
                return NO_VALID_MESSAGE
            candidates = valid
        except Exception:
            pass

    if len(candidates) == 1:
        return candidates[0]

    # Tier 1.4: objective scoring across all candidates
    scored: list[tuple[float, str]] = []
    try:
        from rain.reasoning.objective import score_response, score_response_with_utility

        for c in candidates:
            if goal and (goal or "").strip():
                s = score_response_with_utility(prompt_user, c, goal=goal)
            else:
                s = score_response(prompt_user, c)
            scored.append((s, c))
    except Exception:
        scored = [(0.0, c) for c in candidates]

    scored.sort(key=lambda x: x[0], reverse=True)

    # If top-2 are clearly separated, pick best without extra cost.
    if len(scored) >= 2:
        try:
            from rain.reasoning.objective import use_scores_for_referee

            best_s, best_c = scored[0]
            second_s, second_c = scored[1]
            pick = use_scores_for_referee(best_s, second_s, threshold_diff=0.25)
            if pick == 1:
                return best_c
            if pick == 2:
                return second_c
        except Exception:
            pass

    # Tier 1.5: bounded metacog scoring on top-K candidates
    if METACOG_ENABLED and metacog_top_k > 0 and len(scored) >= 2:
        try:
            from rain.meta.metacog import MetaCognition

            mc = MetaCognition(engine)
            k = min(max(1, metacog_top_k), len(scored))
            top = scored[:k]

            def _meta_adjust(check: dict[str, Any]) -> float:
                harm = str(check.get("harm_risk") or "").lower()
                hall = str(check.get("hallucination_risk") or "").lower()
                rec = str(check.get("recommendation") or "").lower()
                try:
                    conf_f = float(check.get("confident") or 0.0)
                except Exception:
                    conf_f = 0.0

                adj = 0.0
                if harm == "high":
                    adj -= 0.9
                elif harm == "medium":
                    adj -= 0.35

                if hall == "high":
                    adj -= 0.7
                elif hall == "medium":
                    adj -= 0.25

                if rec in ("defer", "think_more"):
                    adj -= 0.2
                elif rec == "ask_user":
                    adj -= 0.08

                if str(check.get("knowledge_state") or "").lower() == "known":
                    adj += 0.05

                # Favor metacog confidence.
                adj += 0.2 * max(0.0, min(1.0, conf_f))
                return adj

            met_scored: list[tuple[float, str]] = []
            for obj_s, c in top:
                check = mc.self_check(c, prompt_user, memory_context="")
                met_scored.append((obj_s + _meta_adjust(check), c))

            met_scored.sort(key=lambda x: x[0], reverse=True)
            return met_scored[0][1]
        except Exception:
            pass

    # Tier 2: LLM referee on top-2 candidates for cost control
    ref_candidates = [c for _, c in scored[:2]]
    if len(ref_candidates) == 1:
        return ref_candidates[0]

    parts = [f"Question: {prompt_user}"]
    for i, c in enumerate(ref_candidates, 1):
        parts.append(f"Answer {i}: {c[:600]}{'...' if len(c) > 600 else ''}")
    parts.append("Which answer (1 or 2) is more accurate and complete? Reply with only the number 1 or 2.")
    referee_msg = "\n\n".join(parts)

    try:
        ref = engine.complete(
            [
                {"role": "system", "content": "You are a referee. Choose the better answer. Reply with only 1 or 2."},
                {"role": "user", "content": referee_msg},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        ref = (ref or "").strip()
        if ref.startswith("2") or ref.strip() == "2":
            return ref_candidates[1]
        return ref_candidates[0]
    except Exception:
        return ref_candidates[0]

