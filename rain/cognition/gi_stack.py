"""
GI stack — orchestration modes (answer / verify / defer / ask / tools).

Gated by `RAIN_GI_STACK` in `rain.config`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EpistemicMode(str, Enum):
    ANSWER = "answer"
    VERIFY = "verify"
    DEFER = "defer"
    ASK = "ask"
    TOOLS = "tools"


@dataclass
class GIOrchestrationState:
    mode: EpistemicMode = EpistemicMode.ANSWER
    confidence_hint: float = 0.5
    reasons: list[str] = field(default_factory=list)
    use_tools: bool = False
    use_memory: bool = False
    prompt_complexity: int = 0


def _score_prompt_complexity(prompt: str) -> int:
    p = (prompt or "").strip()
    if not p:
        return 0
    score = min(5, len(p) // 800)
    low = p.lower()
    heavy = (
        "prove ", "theorem", "constraint", "step-by-step", "bayes", "derive ",
        "implement", "debug", "security", "medical", "legal ", "investment",
    )
    for h in heavy:
        if h in low:
            score += 1
    if "?" in p and len(p) > 200:
        score += 1
    return min(12, score)


def decide_epistemic_mode(
    prompt: str,
    *,
    use_tools: bool,
    use_memory: bool,
    safety_blocked: bool = False,
) -> GIOrchestrationState:
    reasons: list[str] = []
    pc = _score_prompt_complexity(prompt)

    if safety_blocked:
        return GIOrchestrationState(
            mode=EpistemicMode.DEFER,
            confidence_hint=0.0,
            reasons=["safety_blocked"],
            use_tools=False,
            use_memory=use_memory,
            prompt_complexity=pc,
        )

    if use_tools:
        reasons.append("tools_requested")
        return GIOrchestrationState(
            mode=EpistemicMode.TOOLS,
            confidence_hint=0.55,
            reasons=reasons,
            use_tools=True,
            use_memory=use_memory,
            prompt_complexity=pc,
        )

    if pc >= 6:
        reasons.append("high_complexity→verify_bias")
        return GIOrchestrationState(
            mode=EpistemicMode.VERIFY,
            confidence_hint=0.45,
            reasons=reasons,
            use_tools=False,
            use_memory=use_memory,
            prompt_complexity=pc,
        )

    pl = (prompt or "").strip()
    if len(pl) < 25 and "?" in pl:
        reasons.append("underspecified_question")
        return GIOrchestrationState(
            mode=EpistemicMode.ASK,
            confidence_hint=0.35,
            reasons=reasons,
            use_tools=False,
            use_memory=use_memory,
            prompt_complexity=pc,
        )

    reasons.append("default_answer")
    return GIOrchestrationState(
        mode=EpistemicMode.ANSWER,
        confidence_hint=0.6,
        reasons=reasons,
        use_tools=False,
        use_memory=use_memory,
        prompt_complexity=pc,
    )


def gi_system_addon(prompt: str, state: GIOrchestrationState) -> str:
    lines = [
        "\n\n[GI stack — orchestration]",
        f"- Epistemic mode for this turn: {state.mode.value} (heuristic).",
        f"- Prompt complexity score: {state.prompt_complexity}.",
        "- Separate: (1) retrieved/remembered facts, (2) inferences, (3) actions/tools.",
        "- If mode is defer: state limits and unknowns; do not fake certainty.",
        "- If mode is ask: one precise clarifying question before a long answer.",
    ]
    return "\n".join(lines)


def should_force_verification_heuristic(state: GIOrchestrationState | None) -> bool:
    if state is None:
        return False
    return state.mode == EpistemicMode.VERIFY
