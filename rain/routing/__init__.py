"""Compute routing — classical vs QPU. Rain delegates hard optimization to the right hardware."""

from rain.routing.compute_router import (
    compute_route,
    ComputeRouteResult,
    ALL_HINTS,
    ROUTING_KEYWORDS,
)
from rain.routing.qaoa_planner import qaoa_solve, QAOAResult, SUPPORTED_PROBLEM_TYPES

__all__ = [
    "compute_route",
    "ComputeRouteResult",
    "qaoa_solve",
    "QAOAResult",
    "ALL_HINTS",
    "ROUTING_KEYWORDS",
    "SUPPORTED_PROBLEM_TYPES",
]
