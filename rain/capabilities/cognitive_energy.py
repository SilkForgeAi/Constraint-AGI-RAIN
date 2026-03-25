"""Cognitive Energy Model — attention and compute budget, prioritization, focus switching.

Tracks token/compute budget, priority queue for tasks, and focus state.
Used before think() to check can_afford(); after think() to spend(actual).
Enables dynamic attention allocation and cognitive load awareness.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

# Default budget: refill so long-running sessions don't starve
DEFAULT_TOTAL_TOKENS = 100_000
DEFAULT_REFILL_RATE = 5_000  # per refill
DEFAULT_REFILL_INTERVAL_SECONDS = 60.0


@dataclass
class TaskItem:
    """Single item in priority queue: id, priority (higher = more important), token_estimate."""
    id: str
    priority: int
    token_estimate: int
    created: float = field(default_factory=time.monotonic)


class CognitiveEnergyModel:
    """
    Token/compute budget with refill. Priority queue for pending tasks.
    Focus state: current_topic or current_goal; focus_switch() optionally spends a small cost.
    """

    def __init__(
        self,
        total_tokens: int = DEFAULT_TOTAL_TOKENS,
        refill_rate: int = DEFAULT_REFILL_RATE,
        refill_interval_seconds: float = DEFAULT_REFILL_INTERVAL_SECONDS,
    ):
        self._total = total_tokens
        self._refill_rate = refill_rate
        self._refill_interval = refill_interval_seconds
        self._remaining = total_tokens
        self._last_refill = time.monotonic()
        self._lock = threading.RLock()
        self._priority_queue: list[TaskItem] = []
        self._max_queue = 20
        self._focus: str = ""
        self._focus_switch_cost = 50  # tokens "spent" when switching focus

    def refill(self) -> None:
        """Refill budget by refill_rate if enough time has passed."""
        with self._lock:
            now = time.monotonic()
            if now - self._last_refill >= self._refill_interval:
                self._remaining = min(self._total, self._remaining + self._refill_rate)
                self._last_refill = now

    def spend(self, amount: int) -> None:
        """Deduct tokens used. Refill first if interval passed."""
        self.refill()
        with self._lock:
            self._remaining = max(0, self._remaining - amount)

    def can_afford(self, estimated_tokens: int) -> bool:
        """Return True if budget can cover estimated tokens (after refill)."""
        self.refill()
        with self._lock:
            return self._remaining >= estimated_tokens

    def remaining(self) -> int:
        """Current remaining budget."""
        self.refill()
        with self._lock:
            return self._remaining

    def add_task(self, task_id: str, priority: int, token_estimate: int) -> None:
        """Add task to priority queue. Higher priority first."""
        with self._lock:
            self._priority_queue.append(TaskItem(task_id, priority, token_estimate))
            self._priority_queue.sort(key=lambda t: (-t.priority, t.created))
            if len(self._priority_queue) > self._max_queue:
                self._priority_queue.pop()

    def next_task(self) -> TaskItem | None:
        """Pop and return highest-priority task, or None."""
        self.refill()
        with self._lock:
            if not self._priority_queue:
                return None
            return self._priority_queue.pop(0)

    def set_focus(self, topic_or_goal: str) -> None:
        """Set current focus (topic or goal)."""
        with self._lock:
            self._focus = (topic_or_goal or "")[:200]

    def get_focus(self) -> str:
        return self._focus

    def focus_switch(self, new_focus: str) -> None:
        """
        Switch focus to new topic/goal. Optionally spend a small cost to model
        attention switching. Call when user changes topic or goal.
        """
        with self._lock:
            old = self._focus
            self._focus = (new_focus or "")[:200]
            if old != self._focus and self._focus:
                self._remaining = max(0, self._remaining - self._focus_switch_cost)

    def get_status_for_prompt(self, max_length: int = 200) -> str:
        """Short status for prompt: remaining budget, focus, queue length."""
        self.refill()
        with self._lock:
            parts = [
                f"Cognitive budget: {self._remaining} tokens remaining.",
                f"Focus: {self._focus or 'none'}.",
            ]
            if self._priority_queue:
                parts.append(f"Pending tasks: {len(self._priority_queue)} (priority-ordered).")
            out = " ".join(parts)
            return out[:max_length] if len(out) > max_length else out


def get_cognitive_energy_model() -> CognitiveEnergyModel:
    """Factory from config."""
    try:
        from rain import config
        total = int(getattr(config, "COGNITIVE_ENERGY_TOTAL_TOKENS", DEFAULT_TOTAL_TOKENS) or DEFAULT_TOTAL_TOKENS)
        refill = int(getattr(config, "COGNITIVE_ENERGY_REFILL_RATE", DEFAULT_REFILL_RATE) or DEFAULT_REFILL_RATE)
        interval = float(getattr(config, "COGNITIVE_ENERGY_REFILL_INTERVAL_SECONDS", DEFAULT_REFILL_INTERVAL_SECONDS) or DEFAULT_REFILL_INTERVAL_SECONDS)
    except Exception:
        total = DEFAULT_TOTAL_TOKENS
        refill = DEFAULT_REFILL_RATE
        interval = DEFAULT_REFILL_INTERVAL_SECONDS
    return CognitiveEnergyModel(total_tokens=total, refill_rate=refill, refill_interval_seconds=interval)
