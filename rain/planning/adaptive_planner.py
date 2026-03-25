"""Adaptive Planning System — long-horizon planning with recursive refinement.

When outcomes diverge from world-model expectations, re-plan (recursive refinement).
Still user-goal only; checkpoints and max steps apply. Multi-phase: plan -> execute N steps -> compare -> re-plan if needed.
"""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from rain.world.simulator import WorldSimulator


def adaptive_plan(
    goal: str,
    get_planner_steps: Callable[[str, str], list[dict]],
    execute_steps: Callable[[list[dict], int], tuple[str, list[str], bool]],
    simulator: "WorldSimulator | None" = None,
    context: str = "",
    max_phases: int = 3,
    horizon_steps_per_phase: int = 10,
    divergence_threshold: str = "low",
) -> tuple[str, list[str], list[list[dict]]]:
    """
    Multi-phase adaptive planning:
    1. Get plan from get_planner_steps(goal, context).
    2. Execute up to horizon_steps_per_phase steps via execute_steps(steps, max_steps).
       execute_steps returns (final_response, step_log, completed_successfully).
    3. If world-model rollout confidence is "low" or outcome diverges, re-plan (next phase).
    4. Repeat until completed_successfully or max_phases reached.

    Returns (final_response, step_log, all_plans_used).
    """
    all_plans: list[list[dict]] = []
    step_log: list[str] = []
    response = ""

    for phase in range(max_phases):
        steps = get_planner_steps(goal, context)
        if not steps or (len(steps) == 1 and steps[0].get("action", "").startswith("[Escalation]")):
            response = steps[0]["action"] if steps else "No plan generated."
            break
        all_plans.append(steps)
        response, step_log, completed = execute_steps(steps, horizon_steps_per_phase)
        if completed:
            break
        # Optionally check world-model confidence for divergence; if low, re-plan
        if simulator and phase < max_phases - 1:
            try:
                from rain.planning.planner import score_plan_with_world_model
                actions = [s.get("action", "") for s in steps if s.get("action")]
                wm_confidence, _ = score_plan_with_world_model(
                    goal, steps, simulator, context=context, max_rollout_steps=min(5, len(actions))
                )
                if wm_confidence == divergence_threshold:
                    step_log.append(f"[Adaptive] Phase {phase + 1}: world model low confidence; re-planning.")
                    context = context + "\nPrevious attempt: " + response[:300]
                    continue
            except Exception:
                pass
        break

    return (response, step_log, all_plans)
