"""Observation buffer — last N tool results and observations for grounding.

Ties understanding to use: tool outputs and observations update context for next step.
SAFETY: Read-only buffer; no execution. Used to ground world model and prompts.
"""

from __future__ import annotations

from collections import deque
from typing import Any

# Max observations to keep (avoid unbounded growth)
MAX_OBSERVATIONS = 20


class ObservationBuffer:
    """Holds last N tool results and optional text observations for grounding."""

    def __init__(self, max_len: int = MAX_OBSERVATIONS) -> None:
        self._buf: deque[dict[str, Any]] = deque(maxlen=max_len)

    def append_tool_result(self, tool: str, result: str, summary: str = "") -> None:
        """Record a tool call result."""
        self._buf.append({
            "type": "tool",
            "tool": tool,
            "result": result[:2000] if result else "",
            "summary": summary[:200] if summary else "",
        })

    def append_observation(self, text: str) -> None:
        """Record a text observation (e.g. from environment or user)."""
        self._buf.append({"type": "observation", "text": text[:1000]})

    def get_grounding_context(self, last_n: int = 5) -> str:
        """Return formatted string of recent observations for prompt injection."""
        if not self._buf:
            return ""
        recent = list(self._buf)[-last_n:]
        lines = ["Recent observations (use for grounding):"]
        for i, obs in enumerate(recent, 1):
            if obs.get("type") == "tool":
                lines.append(f"  {i}. Tool {obs.get('tool', '')}: {obs.get('summary') or obs.get('result', '')[:150]}")
            else:
                lines.append(f"  {i}. {obs.get('text', '')[:200]}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear buffer (e.g. new session)."""
        self._buf.clear()


def world_state_from_observations(
    observation_buffer: ObservationBuffer,
    goal: str = "",
    last_n: int = 5,
) -> dict:
    """
    Build a world-state dict from observation buffer (grounding: observations -> state).
    Used to seed simulator or planner with observed context. Returns same schema as make_initial_state.
    """
    from rain.world.simulator import make_initial_state
    ctx = observation_buffer.get_grounding_context(last_n=last_n)
    return make_initial_state(goal=goal, context=ctx)


def register_observation(buffer: ObservationBuffer, text: str) -> None:
    """Perception stub: register a text observation (e.g. from environment or sensor)."""
    buffer.append_observation(text)
