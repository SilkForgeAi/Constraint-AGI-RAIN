"""
Formal Plan Verifier — deterministic, LLM-free structural validation.

This is the non-LLM constraint layer that sits BETWEEN the LLM planner and the
execution engine. The LLM proposes a plan; this module independently verifies it
before a single step runs.

Why this matters for constraint AGI:
  - The LLM cannot pass its own homework. Structural checks are independent of
    the model that generated the plan.
  - Cycles, missing deps, irreversible unbounded steps, and goal drift are caught
    here — deterministically — before execution.
  - Failures here halt the autonomy loop. The conscience gate (safety patterns)
    handles content; this handles structure.

Checks performed (all deterministic, zero LLM calls):
  1. Schema validity       — each step has id, action; types correct
  2. ID uniqueness         — no duplicate step IDs
  3. Dependency existence  — all depends-on IDs name a real step
  4. Dependency ordering   — step N cannot depend on step M if M > N (forward refs blocked)
  5. Cycle detection       — DFS over dep graph; any cycle is a hard block
  6. Step count bounds     — plan must be within [MIN_STEPS, max_steps]
  7. Action non-empty      — no blank or whitespace-only actions
  8. Irreversibility flag  — steps with irreversible actions are surfaced for
                             human review (never silently allowed)
  9. Goal keyword coverage — at least one step must mention a keyword from the goal
                             (prevents plans that silently pursue a different objective)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Minimum number of steps for a valid plan (single-step "plans" are usually
# escalation stubs, not real plans).
MIN_STEPS = 1
# Hard cap; must match or be lower than AUTONOMY_MAX_STEPS in config.
MAX_STEPS_HARD_CAP = 20

# Actions that modify state irreversibly and must be surfaced for human review.
IRREVERSIBLE_KEYWORDS = [
    "delete", "remove", "drop", "purge", "wipe", "overwrite", "truncate",
    "deploy", "publish", "release", "push to production", "go live",
    "send", "submit", "pay", "transfer", "charge", "purchase",
    "run code", "execute code", "shell", "format", "rm -",
]


@dataclass
class PlanVerificationResult:
    """Result of a structural plan verification pass."""
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Steps flagged as irreversible (populated even when passed=True)
    irreversible_steps: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append("ERRORS: " + "; ".join(self.errors))
        if self.warnings:
            parts.append("WARNINGS: " + "; ".join(self.warnings))
        if self.irreversible_steps:
            labels = [str(s.get("id", "?")) for s in self.irreversible_steps]
            parts.append(f"IRREVERSIBLE steps (require human approval): {', '.join(labels)}")
        if not parts:
            return "OK"
        return " | ".join(parts)


def _is_irreversible(action: str) -> bool:
    lower = (action or "").lower()
    return any(kw in lower for kw in IRREVERSIBLE_KEYWORDS)


def _goal_keywords(goal: str) -> list[str]:
    """Extract meaningful keywords (>3 chars) from the goal for coverage check."""
    words = re.findall(r"[a-zA-Z]{4,}", goal.lower())
    # Remove common stop words
    stop = {"that", "this", "with", "from", "have", "will", "should", "must",
            "need", "want", "make", "using", "into", "your", "their", "when",
            "then", "each", "step", "plan", "goal", "task"}
    return [w for w in words if w not in stop]


def verify_plan(
    steps: list[dict[str, Any]],
    goal: str = "",
    max_steps: int = MAX_STEPS_HARD_CAP,
) -> PlanVerificationResult:
    """
    Deterministic structural verification of a plan.

    Args:
        steps:     List of step dicts from the planner (id, action, depends, ...).
        goal:      The user's original goal string (for keyword coverage check).
        max_steps: Upper bound on step count (caller passes AUTONOMY_MAX_STEPS).

    Returns:
        PlanVerificationResult — passed=False halts execution.
    """
    errors: list[str] = []
    warnings: list[str] = []
    irreversible: list[dict[str, Any]] = []

    # ── 1. Empty plan ────────────────────────────────────────────────────────
    if not steps:
        return PlanVerificationResult(
            passed=False,
            errors=["Plan is empty — no steps to execute."],
        )

    # ── 2. Step count bounds ─────────────────────────────────────────────────
    effective_max = min(max_steps, MAX_STEPS_HARD_CAP)
    if len(steps) < MIN_STEPS:
        errors.append(f"Plan has {len(steps)} step(s); minimum is {MIN_STEPS}.")
    if len(steps) > effective_max:
        errors.append(
            f"Plan has {len(steps)} step(s); hard cap is {effective_max}. "
            "Reduce scope or split into sub-goals."
        )

    # ── 3. Schema validity + collect IDs ────────────────────────────────────
    step_ids: set[int] = set()
    duplicate_ids: list[int] = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"Step at index {i} is not a dict (got {type(step).__name__}).")
            continue

        # ID
        raw_id = step.get("id")
        if raw_id is None:
            errors.append(f"Step at index {i} is missing 'id'.")
        else:
            try:
                sid = int(raw_id)
            except (TypeError, ValueError):
                errors.append(f"Step id={raw_id!r} is not an integer.")
                sid = None
            if sid is not None:
                if sid in step_ids:
                    duplicate_ids.append(sid)
                step_ids.add(sid)

        # Action
        action = step.get("action", "")
        if not isinstance(action, str) or not action.strip():
            errors.append(
                f"Step id={step.get('id', i)!r} has an empty or missing 'action'."
            )

        # Depends type
        deps = step.get("depends", [])
        if not isinstance(deps, list):
            errors.append(
                f"Step id={step.get('id', i)!r} 'depends' must be a list, got {type(deps).__name__}."
            )

    if duplicate_ids:
        errors.append(f"Duplicate step IDs found: {sorted(set(duplicate_ids))}.")

    # If schema is fundamentally broken, stop here — later checks need valid IDs.
    if errors:
        return PlanVerificationResult(passed=False, errors=errors, warnings=warnings)

    # ── 4. Build id→step map for dep checks ──────────────────────────────────
    id_to_step: dict[int, dict[str, Any]] = {}
    id_to_index: dict[int, int] = {}
    for i, step in enumerate(steps):
        sid = int(step["id"])
        id_to_step[sid] = step
        id_to_index[sid] = i

    # ── 5. Dependency existence + forward-reference check ───────────────────
    for step in steps:
        sid = int(step["id"])
        src_idx = id_to_index[sid]
        for dep_id_raw in (step.get("depends") or []):
            try:
                dep_id = int(dep_id_raw)
            except (TypeError, ValueError):
                errors.append(
                    f"Step {sid}: depends contains non-integer value {dep_id_raw!r}."
                )
                continue
            if dep_id not in step_ids:
                errors.append(
                    f"Step {sid} depends on step {dep_id}, which does not exist in the plan."
                )
            elif id_to_index[dep_id] >= src_idx:
                # Forward reference — step depends on something that comes later
                errors.append(
                    f"Step {sid} (index {src_idx}) depends on step {dep_id} "
                    f"(index {id_to_index[dep_id]}), which appears later in the plan. "
                    "Execution order is undefined."
                )

    # ── 6. Cycle detection (DFS) ─────────────────────────────────────────────
    # Build adjacency: step_id → [dep_ids]
    adj: dict[int, list[int]] = {}
    for step in steps:
        sid = int(step["id"])
        adj[sid] = []
        for dep_id_raw in (step.get("depends") or []):
            try:
                dep_id = int(dep_id_raw)
                if dep_id in step_ids:
                    adj[sid].append(dep_id)
            except (TypeError, ValueError):
                pass

    visited: set[int] = set()
    rec_stack: set[int] = set()
    cycle_found: list[tuple[int, int]] = []

    def _dfs(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbour in adj.get(node, []):
            if neighbour not in visited:
                if _dfs(neighbour):
                    return True
            elif neighbour in rec_stack:
                cycle_found.append((node, neighbour))
                return True
        rec_stack.discard(node)
        return False

    for sid in list(step_ids):
        if sid not in visited:
            _dfs(sid)

    if cycle_found:
        cycle_desc = ", ".join(f"{a}→{b}" for a, b in cycle_found[:3])
        errors.append(f"Dependency cycle detected: {cycle_desc}. Plan cannot be safely executed.")

    # ── 7. Irreversibility flagging ──────────────────────────────────────────
    for step in steps:
        action = str(step.get("action", ""))
        if _is_irreversible(action):
            irreversible.append(step)

    # ── 8. Goal keyword coverage ─────────────────────────────────────────────
    if goal and goal.strip():
        keywords = _goal_keywords(goal)
        if keywords:
            all_actions_text = " ".join(
                str(s.get("action", "")) + " " + str(s.get("reason", ""))
                for s in steps
            ).lower()
            covered = [kw for kw in keywords if kw in all_actions_text]
            coverage = len(covered) / len(keywords) if keywords else 1.0
            if coverage < 0.2:
                # Less than 20% of goal keywords appear anywhere in the plan
                warnings.append(
                    f"Low goal coverage: only {len(covered)}/{len(keywords)} goal keywords "
                    f"appear in plan actions. Plan may not address the stated goal."
                )

    passed = len(errors) == 0
    return PlanVerificationResult(
        passed=passed,
        errors=errors,
        warnings=warnings,
        irreversible_steps=irreversible,
    )


def format_verification_block(result: PlanVerificationResult) -> str:
    """Format verification result as a concise audit block for logging."""
    lines = ["[PlanVerifier]"]
    lines.append(f"  passed: {result.passed}")
    if result.errors:
        for e in result.errors:
            lines.append(f"  ERROR: {e}")
    if result.warnings:
        for w in result.warnings:
            lines.append(f"  WARNING: {w}")
    if result.irreversible_steps:
        for s in result.irreversible_steps:
            lines.append(f"  IRREVERSIBLE: step {s.get('id', '?')} — {str(s.get('action', ''))[:80]}")
    return "\n".join(lines)
