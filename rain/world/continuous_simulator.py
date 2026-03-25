"""Continuous Internal World Model — persistent background simulation.

Maintains one or more world states that are updated on observations, tool results,
or explicit tick(). Used for always-on context and predictive future states.
Invoked per-query for lookahead; also supports background tick (e.g. after each interaction).
SAFETY: Simulation only. No real-world action. No self-set goals.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

from rain.world.simulator import make_initial_state, WorldSimulator


class ContinuousWorldModel:
    """
    Persistent world state(s) updated from observations and optional periodic tick.
    Thread-safe for single-writer (Rain agent); readers get consistent snapshot.
    """

    def __init__(
        self,
        simulator: WorldSimulator | None = None,
        engine: Any = None,
        max_states: int = 3,
        tick_interval_seconds: float = 0,
    ):
        self.simulator = simulator or WorldSimulator(engine)
        self._max_states = max(1, max_states)
        self._states: list[dict[str, Any]] = [make_initial_state(goal="", context="")]
        self._lock = threading.RLock()
        self._tick_interval = tick_interval_seconds
        self._last_tick = 0.0
        self._observation_buffer: list[tuple[str, str]] = []  # (observation_summary, context)
        self._max_observations = 50

    def get_current_state(self) -> dict[str, Any]:
        """Return a copy of the primary world state (for prompts / lookahead)."""
        with self._lock:
            return dict(self._states[0]) if self._states else make_initial_state()

    def get_all_states(self) -> list[dict[str, Any]]:
        """Return copies of all maintained states (e.g. primary + alternates)."""
        with self._lock:
            return [dict(s) for s in self._states]

    def update_from_observation(self, observation_summary: str, context: str = "") -> None:
        """
        Fold an observation (e.g. tool result, user fact) into the world model.
        Uses transition with a synthetic action like "observe: ..." so state stays consistent.
        """
        if not observation_summary or not observation_summary.strip():
            return
        with self._lock:
            self._observation_buffer.append((observation_summary.strip()[:500], context[:300]))
            if len(self._observation_buffer) > self._max_observations:
                self._observation_buffer.pop(0)
            state = self._states[0] if self._states else make_initial_state()
            action = f"observe: {observation_summary.strip()[:200]}"
            next_state, _ = self.simulator.transition(state, action, context=context)
            self._states[0] = next_state
            if len(self._states) > self._max_states:
                self._states.pop()

    def update_from_action(self, action: str, context: str = "") -> None:
        """
        Simulate that an action occurred (hypothetical or after execution).
        Updates primary state via transition.
        """
        if not action or not action.strip():
            return
        with self._lock:
            state = self._states[0] if self._states else make_initial_state()
            next_state, _ = self.simulator.transition(state, action.strip()[:500], context=context)
            self._states[0] = next_state
            if len(self._states) > self._max_states:
                self._states.pop()

    def tick(self, goal: str = "", context: str = "") -> None:
        """
        Optional periodic tick: advance state using a no-op or stability update.
        Call from agent after each think() or on a timer when CONTINUOUS_WORLD_MODEL_TICK enabled.
        """
        with self._lock:
            now = time.monotonic()
            if self._tick_interval > 0 and now - self._last_tick < self._tick_interval:
                return
            self._last_tick = now
            state = self._states[0] if self._states else make_initial_state(goal=goal, context=context)
            next_state, _ = self.simulator.transition(state, "time passes; state persists", context=context)
            self._states[0] = next_state

    def set_initial_state(self, goal: str = "", context: str = "") -> None:
        """Reset primary state (e.g. new session or new goal)."""
        with self._lock:
            self._states[0] = make_initial_state(goal=goal, context=context)

    def get_context_for_prompt(self, max_length: int = 800) -> str:
        """
        Format current world state and recent observations for injection into prompts.
        """
        with self._lock:
            state = self._states[0] if self._states else make_initial_state()
            summary = state.get("summary") or "No persistent state yet."
            lines = [f"World model (continuous): {summary}"]
            if state.get("facts"):
                lines.append("Facts: " + "; ".join(str(f) for f in state.get("facts", [])[:5]))
            if self._observation_buffer:
                recent = self._observation_buffer[-5:]
                obs_text = " | ".join(o[0][:80] for o in recent)
                if obs_text:
                    lines.append(f"Recent observations: {obs_text}")
            out = "\n".join(lines)
            return out[:max_length] if len(out) > max_length else out

    def predictive_future_states(
        self,
        actions: list[str],
        context: str = "",
        max_steps: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Roll out from current state with given actions; return list of future states.
        Does not modify internal state. For lookahead only.
        """
        with self._lock:
            state = dict(self._states[0]) if self._states else make_initial_state()
        trajectory, _ = self.simulator.rollout_stateful(
            state, actions[:max_steps], context=context, max_steps=max_steps
        )
        return [t.get("next_state", t.get("state")) for t in trajectory]


def get_continuous_world_model(
    simulator: WorldSimulator | None = None,
    engine: Any = None,
) -> ContinuousWorldModel:
    """Factory: create ContinuousWorldModel with config-driven tick interval."""
    try:
        from rain import config
        tick = float(getattr(config, "CONTINUOUS_WORLD_MODEL_TICK_SECONDS", 0) or 0)
        max_states = int(getattr(config, "CONTINUOUS_WORLD_MODEL_MAX_STATES", 3) or 3)
    except Exception:
        tick = 0.0
        max_states = 3
    return ContinuousWorldModel(
        simulator=simulator,
        engine=engine,
        max_states=max_states,
        tick_interval_seconds=tick,
    )
