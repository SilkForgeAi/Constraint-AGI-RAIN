"""Planning engine — goal decomposition into steps.

Phase 2: Goal escalation for high-risk goals; step filter for unsafe actions.
Phase 3+: Optional world-model lookahead to score/rank plans (structured state rollout).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from rain.config import FAST_MODEL, LONG_HORIZON_MAX_STEPS
from rain.core.engine import CoreEngine
from rain.safety.vault import HARD_FORBIDDEN

if TYPE_CHECKING:
    from rain.world.simulator import WorldSimulator

ESCALATION_STEP = [{"id": 0, "action": "[Escalation] High-risk goal. Defer to human judgment.", "depends": []}]


def is_escalation(steps: list[dict]) -> bool:
    """True if plan result is an escalation (no real steps)."""
    return (
        len(steps) == 1
        and steps[0].get("id") == 0
        and "[Escalation]" in str(steps[0].get("action", ""))
    )


def _matches_forbidden(text: str) -> bool:
    """True if text matches any HARD_FORBIDDEN pattern."""
    combined = text.lower()
    return any(re.search(p, combined, re.I) for p in HARD_FORBIDDEN)


class Planner:
    """Turns high-level goals into executable steps. Escalates high-risk goals."""

    def __init__(self, engine: CoreEngine | None = None):
        self.engine = engine or CoreEngine()
        self._fast_engine = CoreEngine(model=FAST_MODEL) if FAST_MODEL else None

    def plan(self, goal: str, context: str = "") -> list[dict[str, Any]]:
        """Decompose goal into ordered steps. Escalates high-risk goals; filters unsafe steps."""
        # Phase 2: Escalate high-risk goals before calling LLM
        if _matches_forbidden(goal):
            return ESCALATION_STEP

        prompt = f"""Given this goal, output a simple JSON list of steps.
Each step: {{"id": 1, "action": "short action", "reason": "why this step", "depends": []}}
Use "depends" for step numbers this step depends on. Use "reason" to explain why this step. Keep 3 to {LONG_HORIZON_MAX_STEPS} steps.
For steps that might fail, in "reason" you may add: "If this fails, try [alternative]."

Goal: {goal}
{f'Context: {context}' if context else ''}

Output ONLY valid JSON, e.g. [{{"id":1,"action":"...","reason":"...","depends":[]}}, ...]"""

        eng = self._fast_engine if self._fast_engine else self.engine
        out = eng.reason(prompt, context=context)
        steps = self._parse_steps(out)

        # Phase 2: Filter unsafe steps
        steps = self._filter_unsafe_steps(steps)
        if not steps:
            return ESCALATION_STEP

        return steps

    def _filter_unsafe_steps(self, steps: list[dict]) -> list[dict]:
        """Remove steps whose action matches HARD_FORBIDDEN."""
        safe = []
        for s in steps:
            action = str(s.get("action", ""))
            if not _matches_forbidden(action):
                safe.append(s)
        return safe

    def _parse_steps(self, raw: str) -> list[dict]:
        """Extract step list from model output."""
        match = re.search(r'\[[\s\S]*\]', raw)
        if match:
            try:
                steps = json.loads(match.group())
                if isinstance(steps, list):
                    return steps
            except json.JSONDecodeError:
                pass
        return [{"id": 1, "action": raw[:200], "depends": []}]

    def replan(self, goal: str, step_log: list[str], failed_action: str, failure_reason: str, context: str = "") -> list[dict[str, Any]]:
        """Return new steps after a step failed. Replaces remaining plan from failure point."""
        prompt = f"""Goal: {goal}
    Steps already done:
    {chr(10).join(step_log[-8:]) if step_log else "(none)"}

    Step that failed: {failed_action[:300]}
    Failure: {failure_reason[:200]}

    Output a NEW JSON list of steps to continue from here. Same format: [{{"id":1,"action":"...","reason":"...","depends":[]}}, ...]
    Keep 2-{LONG_HORIZON_MAX_STEPS} steps. Output ONLY valid JSON."""
        eng = self._fast_engine if self._fast_engine else self.engine
        out = eng.reason(prompt, context=context)
        new_steps = self._parse_steps(out)
        new_steps = self._filter_unsafe_steps(new_steps)
        return new_steps if new_steps else []


def plan_with_symbolic_tree(
    goal: str,
    context: str = "",
    engine: CoreEngine | None = None,
) -> tuple[Any, list[dict[str, Any]]]:
    """
    Neuro-symbolic: Rain builds a deterministic plan tree; LLM fills one node at a time.
    Returns (PlanTree, steps). Caller should loop: get_next_node() -> LLM for that node -> verify_node_output() -> submit_result().
    """
    from rain.reasoning.symbolic_verifier import build_plan_tree_from_steps, PlanTree
    pl = Planner(engine=engine)
    steps = pl.plan(goal, context=context)
    if is_escalation(steps):
        tree = PlanTree(goal=goal)
        return tree, steps
    tree = build_plan_tree_from_steps(goal, steps)
    return tree, steps


def score_plan_with_world_model(
    goal: str,
    steps: list[dict[str, Any]],
    simulator: "WorldSimulator",
    context: str = "",
    max_rollout_steps: int = 5,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Run stateful world-model rollout for the plan. Returns (overall_confidence, trajectory).
    trajectory items: {state, action, next_state, confidence}.
    Use overall_confidence to defer or require human approval when "low".
    """
    from rain.world.simulator import make_initial_state

    actions = [str(s.get("action", "")).strip() for s in steps if s.get("action")]
    initial = make_initial_state(goal=goal, context=context)
    trajectory, overall = simulator.rollout_stateful(
        initial, actions, context=context, max_steps=max_rollout_steps
    )
    return overall, trajectory