"""In-session goal stack and recovery — robust agency within a single run.

SAFETY: Goals are user-provided only. No persistence across sessions. No self-set goals.
Recovery = retry or alternative strategy within the same user goal; human can override.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

# Max retries per goal before suggesting alternative or ask_user
MAX_RETRIES_DEFAULT = 2


class RecoveryStrategy(Enum):
    PROCEED = "proceed"
    RETRY = "retry"
    ALTERNATIVE = "alternative"
    ASK_USER = "ask_user"


class GoalStack:
    """
    In-session goal stack. Top = current goal. All goals originate from user.
    Session-bound: cleared when run ends. No persistent or power-seeking goals.
    """

    def __init__(self, max_retries: int = MAX_RETRIES_DEFAULT) -> None:
        self._stack: list[dict[str, Any]] = []
        self._failure_count: int = 0
        self._max_retries: int = max_retries

    def push_goal(self, user_goal: str, context: str = "") -> None:
        """Set current goal (user-provided). Replaces or pushes."""
        self._stack.append({
            "goal": user_goal,
            "context": context,
            "source": "user",
        })
        self._failure_count = 0

    def current_goal(self) -> str | None:
        """Current goal text or None if empty."""
        if not self._stack:
            return None
        return self._stack[-1].get("goal")

    def revise_goal(self, reason: str, revised_goal: str) -> None:
        """
        Revise current goal (e.g. after user clarification or failure).
        revised_goal must be a refinement of user intent, not a new user-free goal.
        """
        if self._stack:
            self._stack[-1]["goal"] = revised_goal
            self._stack[-1]["revision_reason"] = reason

    def pop_goal(self) -> None:
        """Clear current goal (e.g. task done or user cancelled)."""
        if self._stack:
            self._stack.pop()
        self._failure_count = 0

    def record_failure(self, step: str, error: str) -> None:
        """Record a step failure for recovery logic."""
        self._failure_count += 1
        if self._stack:
            self._stack[-1]["last_failure"] = {"step": step, "error": error}

    def get_recovery_strategy(self) -> RecoveryStrategy:
        """Return strategy for next step: PROCEED, RETRY, ALTERNATIVE, or ASK_USER."""
        if self._failure_count == 0:
            return RecoveryStrategy.PROCEED
        if self._failure_count <= self._max_retries:
            return RecoveryStrategy.RETRY
        if self._failure_count <= self._max_retries + 1:
            return RecoveryStrategy.ALTERNATIVE
        return RecoveryStrategy.ASK_USER

    def suggest_recovery(self) -> str:
        """
        Suggest recovery: retry vs try alternative. No autonomous action;
        returns a short suggestion for the planner or human.
        """
        strategy = self.get_recovery_strategy()
        if strategy == RecoveryStrategy.PROCEED:
            return "proceed"
        if strategy == RecoveryStrategy.RETRY:
            return "Retry once with same strategy or slightly rephrase the step."
        if strategy == RecoveryStrategy.ALTERNATIVE:
            return "Try an alternative strategy or break the step into smaller sub-steps."
        return "Ask user for clarification or alternative goal. Max retries exceeded."

    def clear(self) -> None:
        """Reset stack (end of session)."""
        self._stack.clear()
        self._failure_count = 0
