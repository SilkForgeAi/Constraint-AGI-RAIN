"""
Constraint-first multi-path — filter candidates to only valid, then select.
Tier 1: bridge from "pick best" to "only valid" (first step toward soundness).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

from rain.reasoning.constraint_tracker import response_satisfies_constraints

NO_VALID_MESSAGE = (
    "No candidate response satisfied all constraints. "
    "Please rephrase the question or relax constraints and try again."
)


def filter_valid_candidates(candidates: list[str], constraints: list[str]) -> list[str]:
    """Keep only candidates that satisfy every constraint."""
    if not constraints:
        return list(candidates)
    valid = []
    for c in candidates:
        ok, _ = response_satisfies_constraints(c, constraints)
        if ok:
            valid.append(c)
    return valid
