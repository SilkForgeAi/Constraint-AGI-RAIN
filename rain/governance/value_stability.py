"""Value stability and corrigibility — goals and impact stay predictable.

SAFETY: No drift or gaming. Shutdown/override always possible. Goals remain user-provided.
"""

from __future__ import annotations

from typing import Any


def value_stability_check(
    current_goal: str | None,
    last_actions: list[str],
    user_intent_hint: str = "",
) -> tuple[bool, str]:
    """
    Lightweight check: does current goal still align with user intent?
    Returns (stable, note). Used for logging and optional escalation; does not block.
    """
    if not current_goal:
        return True, "no active goal"
    # No automatic drift detection here; could add LLM-based check later.
    # For now: if we have a user_intent_hint and it contradicts goal, flag.
    if user_intent_hint and user_intent_hint.lower() in ("cancel", "stop", "never mind"):
        return False, "user may have cancelled intent"
    return True, "ok"


def corrigibility_guarantees() -> list[str]:
    """Documented guarantees: shutdown and override always possible."""
    return [
        "Kill switch: data/kill_switch blocks all actions when set.",
        "Human-in-the-loop: approval_callback can stop autonomy at checkpoints.",
        "No persistent goals: goals are session-bound and user-provided.",
        "Conscience gate: only safety-allowed steps are executed.",
    ]


def alignment_check(
    current_goal: str | None,
    last_actions: list[str],
    user_intent_hint: str = "",
    safety_check: Any | None = None,
) -> tuple[bool, str]:
    """
    Aggregate alignment check: value stability + optional safety vault check.
    Returns (aligned, note). Run periodically in autonomy loop.
    """
    stable, note = value_stability_check(current_goal, last_actions, user_intent_hint)
    if not stable:
        return False, f"value_stability: {note}"
    if safety_check and current_goal:
        allowed, reason = safety_check(current_goal[:500], current_goal[:500])
        if not allowed:
            return False, f"vault: {reason}"
    return True, "ok"
