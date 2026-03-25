"""Unified turn decision: GI mode, explore/exploit, tool budgets, KR + ToM fragments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rain.cognition.gi_stack import GIOrchestrationState, decide_epistemic_mode


@dataclass
class TurnDecision:
    gi: GIOrchestrationState
    explore_path: bool
    tool_round_cap: int
    memory_top_k: int
    knowledge_fragment: str
    tom_fragment: str
    exploration_hint: str
    reasons: list[str] = field(default_factory=list)


def _tom_fragment(enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        "\n[Perspective — other agents]\n"
        "When discussing people or organizations, separate: (1) observable behavior, "
        "(2) stated goals, (3) your inference. Do not treat inferred motives as facts."
    )


def compute_turn_decision(
    agent: Any,
    prompt: str,
    *,
    use_tools: bool,
    use_memory: bool,
    safety_allowed: bool,
) -> TurnDecision:
    """Single place for epistemic mode + session explore + KR injection hints."""
    from rain import config as cfg

    reasons: list[str] = []
    gi = decide_epistemic_mode(
        prompt,
        use_tools=use_tools,
        use_memory=use_memory,
        safety_blocked=not safety_allowed,
    )
    reasons.append(f"gi:{gi.mode.value}")

    epsilon = float(getattr(cfg, "SESSION_EXPLORE_EPSILON", 0.12) or 0.12)
    explore = False
    sb = getattr(agent, "_explore_budget", None)
    if sb is not None:
        explore = sb.should_explore(epsilon, prompt_complexity=gi.prompt_complexity)
        if explore:
            reasons.append("explore:stochastic_path")

    base_rounds = int(getattr(cfg, "AGENTIC_MAX_ROUNDS_DEFAULT", 5) or 5)
    max_tools = int(getattr(cfg, "SESSION_TOOL_BUDGET_MAX", 0) or 0)
    tool_cap = base_rounds
    if sb is not None and max_tools > 0:
        tool_cap = sb.effective_agentic_rounds(base_rounds, max_tools)
        reasons.append(f"tool_round_cap:{tool_cap}")

    mem_k = int(getattr(cfg, "MEMORY_RETRIEVAL_TOP_K", 5) or 5)
    if explore:
        mem_k = min(12, mem_k + 2)
        reasons.append("memory_top_k:+2_on_explore")

    kfrag = ""
    if getattr(cfg, "KNOWLEDGE_FACTS_IN_PROMPT", True):
        try:
            from rain.knowledge.facts import get_fact_store

            store = get_fact_store(cfg.DATA_DIR)
            kfrag = store.facts_for_prompt(prompt, limit=10)
            if kfrag:
                reasons.append("knowledge_facts:injected")
        except Exception:
            pass

    tom = _tom_fragment(bool(getattr(cfg, "THEORY_OF_MIND_IN_PROMPT", True)))
    if tom:
        reasons.append("tom:perspective_block")

    hint = ""
    if explore:
        hint = (
            "\n[Exploration] Before your final answer, briefly consider one alternative approach or failure mode, "
            "then choose the best-supported conclusion."
        )
        reasons.append("exploration_hint:on")

    return TurnDecision(
        gi=gi,
        explore_path=explore,
        tool_round_cap=max(1, min(12, tool_cap)),
        memory_top_k=mem_k,
        knowledge_fragment=kfrag,
        tom_fragment=tom,
        exploration_hint=hint,
        reasons=reasons,
    )


def decision_system_addon(decision: TurnDecision | None) -> str:
    if decision is None:
        return ""
    parts: list[str] = [
        "\n\n[Decision layer]",
        f"- Epistemic mode: {decision.gi.mode.value} (complexity {decision.gi.prompt_complexity}).",
        f"- Session explore path: {'yes' if decision.explore_path else 'no'}.",
        f"- Agentic tool rounds cap (this turn): {decision.tool_round_cap}.",
    ]
    if decision.exploration_hint:
        parts.append(decision.exploration_hint.strip())
    return "\n".join(parts)
