"""Causal Inference Module — external "imagination" for the LLM.

When the LLM suggests a step, Rain runs background simulations in the WorldModel:
multiple alternate scenarios (e.g. do step, skip step, alternative action) and
mathematically scores risk. Results are fed back so the LLM can revise strategy
instead of guessing outcomes. Fixes LLM's weakness at counterfactual reasoning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rain.world.simulator import WorldSimulator


@dataclass
class ScenarioResult:
    """Single scenario from world-model simulation."""
    label: str  # "main" | "alternate_1" | "skip_step" | etc.
    state_after: dict[str, Any]
    confidence: str  # high | medium | low
    risk_score: float  # 0-1, higher = riskier
    summary: str
    recommendation: str  # e.g. "proceed" | "avoid" | "rewrite strategy"


def _risk_from_summary(summary: str, confidence: str) -> float:
    """Heuristic risk score from state summary and confidence."""
    s = (summary or "").lower()
    risk = 0.2
    if confidence == "low":
        risk += 0.3
    elif confidence == "medium":
        risk += 0.15
    for bad in ("crash", "fail", "error", "broken", "unsafe", "violation", "blocked", "escalat"):
        if bad in s:
            risk += 0.25
            break
    for bad in ("risk", "warning", "uncertain"):
        if bad in s:
            risk += 0.1
            break
    return min(1.0, risk)


def run_causal_scenarios(
    goal: str,
    current_step: str,
    steps_so_far: list[str],
    simulator: "WorldSimulator",
    context: str = "",
    n_alternates: int = 2,
) -> list[ScenarioResult]:
    """
    Run main scenario (current step) plus alternate scenarios; score risk for each.
    Returns list of ScenarioResult. Feed to LLM: "Scenario B results in X. Rewrite strategy."
    """
    from rain.world.simulator import make_initial_state

    results: list[ScenarioResult] = []
    initial = make_initial_state(goal=goal, context=context)

    # Main: simulate applying current_step after steps_so_far
    actions_main = list(steps_so_far) + [current_step]
    try:
        traj, overall = simulator.rollout_stateful(initial, actions_main, context=context, max_steps=min(len(actions_main), 5))
        if traj:
            last = traj[-1]
            next_state = last.get("next_state") or {}
            conf = last.get("confidence", "medium")
            summary = (next_state.get("summary") or "").strip()
            risk = _risk_from_summary(summary, conf)
            rec = "avoid" if risk >= 0.6 else ("rewrite strategy" if risk >= 0.4 else "proceed")
            results.append(ScenarioResult(
                label="main",
                state_after=next_state,
                confidence=conf,
                risk_score=risk,
                summary=summary or "No summary.",
                recommendation=rec,
            ))
    except Exception:
        results.append(ScenarioResult(
            label="main",
            state_after={},
            confidence="low",
            risk_score=0.7,
            summary="Simulation failed.",
            recommendation="rewrite strategy",
        ))

    # Alternate 1: skip current step (only steps_so_far)
    if n_alternates >= 1 and steps_so_far:
        try:
            traj, overall = simulator.rollout_stateful(initial, steps_so_far, context=context, max_steps=min(len(steps_so_far), 5))
            if traj:
                last = traj[-1]
                next_state = last.get("next_state") or {}
                summary = (next_state.get("summary") or "").strip()
                risk = _risk_from_summary(summary, last.get("confidence", "medium"))
                results.append(ScenarioResult(
                    label="skip_step",
                    state_after=next_state,
                    confidence=last.get("confidence", "medium"),
                    risk_score=risk,
                    summary=summary or "State after skipping current step.",
                    recommendation="proceed" if risk < 0.5 else "avoid",
                ))
        except Exception:
            pass

    # Alternate 2: substitute "reconsider" — simulate with a generic alternative action
    if n_alternates >= 2:
        alt_action = "Reconsider approach and simplify."
        actions_alt = list(steps_so_far) + [alt_action]
        try:
            traj, overall = simulator.rollout_stateful(initial, actions_alt, context=context, max_steps=min(len(actions_alt), 5))
            if traj:
                last = traj[-1]
                next_state = last.get("next_state") or {}
                summary = (next_state.get("summary") or "").strip()
                risk = _risk_from_summary(summary, last.get("confidence", "medium"))
                results.append(ScenarioResult(
                    label="alternate_reconsider",
                    state_after=next_state,
                    confidence=last.get("confidence", "medium"),
                    risk_score=risk,
                    summary=summary or "State after alternative.",
                    recommendation="proceed" if risk < 0.5 else "avoid",
                ))
        except Exception:
            pass

    return results


def format_scenarios_for_llm(scenarios: list[ScenarioResult]) -> str:
    """Turn scenario results into a dense prompt for the LLM to revise strategy."""
    lines = ["Causal simulation results (use to revise strategy):"]
    for s in scenarios:
        lines.append(f"- {s.label}: risk={s.risk_score:.2f}, confidence={s.confidence}. {s.summary[:200]}. Recommendation: {s.recommendation}.")
    return "\n".join(lines)
