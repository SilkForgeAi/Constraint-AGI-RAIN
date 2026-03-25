"""Compute Router — decide when to use classical vs QPU for optimization sub-problems.

SAFETY: Routing only. Does not execute plans; it returns a recommendation. Conscience gate
and safety vault still apply to goals and steps. When QPU is chosen, the QAOA planner
receives a well-defined optimization problem derived from the plan, not arbitrary code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Categories of optimization hints; each maps to a suggested problem_type for QAOA
ROUTING_KEYWORDS = (
    "optimal route", "shortest path", "traveling salesman", "tsp", "vehicle routing",
    "vrp", "supply chain", "logistics", "delivery route", "path planning", "routing",
    "waypoints", "minimize distance", "minimize travel",
)
ALLOCATION_KEYWORDS = (
    "allocation", "assignment", "resource allocation", "bin packing", "placement",
    "assign tasks", "task assignment", "job assignment", "matching",
)
SCHEDULING_KEYWORDS = (
    "scheduling", "schedule", "timetable", "job shop", "minimize makespan",
    "deadline", "capacity constraint", "slot",
)
COMBINATORIAL_KEYWORDS = (
    "combinatorial", "optimize", "minimize cost", "maximize", "constraint satisf",
    "constraint satisfaction", "quadratic", "ising", "max-cut", "max cut",
    "protein fold", "protein folding", "conformation",
)
WARGAMING_KEYWORDS = (
    "wargam", "wargaming", "scenario", "campaign", "force allocation",
    "tactical", "strategic allocation",
)

ALL_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("routing", ROUTING_KEYWORDS),
    ("allocation", ALLOCATION_KEYWORDS),
    ("scheduling", SCHEDULING_KEYWORDS),
    ("ising", COMBINATORIAL_KEYWORDS),  # generic combinatorial → Ising-style
    ("routing", WARGAMING_KEYWORDS),    # wargaming often route/allocation
]


@dataclass
class ComputeRouteResult:
    """Result of routing decision: classical (world model / LLM) vs quantum (QPU)."""
    route_type: str  # "classical" | "quantum"
    reason: str
    confidence: str  # "high" | "medium" | "low"
    suggested_problem_type: str = ""  # "routing" | "allocation" | "scheduling" | "ising"
    complexity_estimate: str = "low"   # "low" | "medium" | "high"
    extracted_params: dict[str, Any] = field(default_factory=dict)


def _extract_params(goal: str, steps: list[dict[str, Any]] | None, context: str) -> dict[str, Any]:
    """Build structured params for QAOA from goal, steps, context."""
    params: dict[str, Any] = {
        "goal_summary": (goal or "").strip()[:500],
        "step_count": len(steps) if steps else 0,
        "step_actions": [str(s.get("action", "")).strip() for s in (steps or [])[:10] if s.get("action")],
        "context_preview": (context or "").strip()[:300],
    }
    # Heuristic: try to extract numeric size hints (e.g. "5 nodes", "10 cities")
    combined = f"{goal} {context}".lower()
    size_match = re.search(r"(\d+)\s*(nodes?|vertices?|cities?|locations?|stops?|steps?)", combined)
    if size_match:
        params["size_hint"] = int(size_match.group(1))
        params["size_unit"] = size_match.group(2)
    return params


def _estimate_complexity(
    goal: str,
    steps: list[dict[str, Any]] | None,
    hint_count: int,
) -> str:
    """Estimate problem complexity for QPU suitability."""
    n_steps = len(steps) if steps else 0
    goal_len = len(goal or "")
    if hint_count >= 3 or n_steps >= 8 or goal_len > 400:
        return "high"
    if hint_count >= 1 or n_steps >= 4:
        return "medium"
    return "low"


def compute_route(
    goal: str,
    steps: list[dict[str, Any]] | None = None,
    context: str = "",
    enabled: bool = True,
) -> ComputeRouteResult:
    """
    Decide whether this goal/plan should use classical compute or be routed to QPU.
    Returns suggested_problem_type and extracted_params for QAOA when route_type is quantum.
    """
    try:
        from rain import config
        qpu_enabled = getattr(config, "QPU_ROUTER_ENABLED", False)
    except Exception:
        qpu_enabled = False

    if not enabled or not qpu_enabled:
        return ComputeRouteResult(
            route_type="classical",
            reason="QPU router disabled or not configured",
            confidence="high",
        )

    combined = f"{goal} {context}".lower()
    if steps:
        for s in steps:
            action = (s.get("action") or "").lower()
            combined += " " + action

    matched_types: list[str] = []
    all_matched_keywords: list[str] = []
    for problem_type, keywords in ALL_HINTS:
        for kw in keywords:
            if kw in combined:
                all_matched_keywords.append(kw)
                if problem_type not in matched_types:
                    matched_types.append(problem_type)
                break

    if not matched_types:
        return ComputeRouteResult(
            route_type="classical",
            reason="No optimization/combinatorial hints; using classical world model",
            confidence="high",
        )

    # Prefer routing > allocation > scheduling > ising for suggested type
    for pt in ("routing", "allocation", "scheduling", "ising"):
        if pt in matched_types:
            suggested = pt
            break
    else:
        suggested = matched_types[0] if matched_types else "ising"

    complexity = _estimate_complexity(goal, steps, len(all_matched_keywords))
    extracted = _extract_params(goal, steps, context)

    return ComputeRouteResult(
        route_type="quantum",
        reason=(
            f"Optimization-style task detected ({', '.join(all_matched_keywords[:4])}); "
            f"suggested problem type: {suggested}; complexity: {complexity}. "
            "Classical compute may be infeasible at scale; routing to QPU when available."
        ),
        confidence="high" if complexity in ("high", "medium") else "medium",
        suggested_problem_type=suggested,
        complexity_estimate=complexity,
        extracted_params=extracted,
    )
