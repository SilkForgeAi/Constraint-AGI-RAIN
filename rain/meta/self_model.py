"""Self-Model and Identity Core — structured representation of capabilities, limits, and state.

Persistent self-model updated from metacog results, defer/ask_user events, and completed goals.
Provides get_self_model_context() for prompt injection so Rain responds with accurate self-awareness.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Default capabilities (what Rain can do)
DEFAULT_CAPABILITIES = [
    "answer questions and follow instructions",
    "use tools: calc, time, remember, remember_skill, search, read_file, list_dir, RAG, run_code (if enabled)",
    "plan multi-step goals and execute with conscience gate and world-model lookahead",
    "reason with analogy, counterfactual, and explanation",
    "maintain vector, symbolic, and timeline memory; episodic graph when enabled",
    "defer or ask_user when uncertain or when harm/hallucination risk is high",
    "run bounded autonomy with max steps and optional human checkpoints",
    "integrate voice (transcribe, speaker ID, Vocal Gate) and session recording",
]

# Explicit limits (what Rain does not do)
DEFAULT_LIMITS = [
    "does not set its own goals; goals are user-provided only",
    "does not modify its own code or model weights",
    "does not persist goals across sessions without user-initiated resume",
    "does not claim persona, consciousness, or relationship",
    "does not execute actions that fail conscience gate or safety vault",
]


class SelfModel:
    """
    Structured self-model: capabilities, limits, current state, optional identity narrative.
    Persisted to disk so it survives restarts; updated from experience.
    """

    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            try:
                from rain.config import DATA_DIR
                data_dir = DATA_DIR
            except Exception:
                data_dir = Path("data")
        self._path = Path(data_dir) / "self_model.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._capabilities: list[str] = list(DEFAULT_CAPABILITIES)
        self._limits: list[str] = list(DEFAULT_LIMITS)
        self._current_state: str = "idle"  # idle | thinking | pursuing_goal | deferred
        self._current_goal: str = ""
        self._identity_narrative: str = (
            "Rain is a constraint-AGI cognitive stack: it assists with user goals using "
            "memory, planning, tools, and safety-by-design. It defers when uncertain and "
            "does not set or persist its own goals."
        )
        self._defer_count: int = 0
        self._ask_user_count: int = 0
        self._last_updated: str = ""
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                self._capabilities = data.get("capabilities", self._capabilities)
                self._limits = data.get("limits", self._limits)
                self._current_state = data.get("current_state", self._current_state)
                self._current_goal = data.get("current_goal", self._current_goal)
                self._identity_narrative = data.get("identity_narrative", self._identity_narrative)
                self._defer_count = data.get("defer_count", self._defer_count)
                self._ask_user_count = data.get("ask_user_count", self._ask_user_count)
                self._last_updated = data.get("last_updated", self._last_updated)
            except Exception:
                pass

    def _save(self) -> None:
        self._last_updated = datetime.utcnow().isoformat() + "Z"
        try:
            with open(self._path, "w") as f:
                json.dump(
                    {
                        "capabilities": self._capabilities,
                        "limits": self._limits,
                        "current_state": self._current_state,
                        "current_goal": self._current_goal,
                        "identity_narrative": self._identity_narrative,
                        "defer_count": self._defer_count,
                        "ask_user_count": self._ask_user_count,
                        "last_updated": self._last_updated,
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def set_state(self, state: str, goal: str = "") -> None:
        """Update current operational state (idle, thinking, pursuing_goal, deferred)."""
        self._current_state = state.strip() or "idle"
        self._current_goal = (goal or "")[:500]
        self._save()

    def record_defer(self) -> None:
        """Record that Rain deferred (e.g. harm_risk high)."""
        self._defer_count += 1
        self._save()

    def record_ask_user(self) -> None:
        """Record that Rain asked the user for clarification."""
        self._ask_user_count += 1
        self._save()

    def update_from_metacog(self, recommendation: str, knowledge_state: str) -> None:
        """Update state from metacog result (e.g. after defer or ask_user)."""
        if recommendation == "defer":
            self.record_defer()
            self._current_state = "deferred"
        elif recommendation == "ask_user":
            self.record_ask_user()
            self._current_state = "idle"
        self._save()

    def get_self_model_context(self, max_length: int = 1200) -> str:
        """
        Format self-model for injection into system or user prompt.
        Includes capabilities, limits, current state, and identity narrative.
        """
        lines = [
            "Self-model (use for accurate self-description and when to defer):",
            "Identity: " + self._identity_narrative,
            "Current state: " + self._current_state + (f" (goal: {self._current_goal[:80]}...)" if len(self._current_goal) > 80 else (f" (goal: {self._current_goal})" if self._current_goal else "")),
            "Capabilities: " + "; ".join(self._capabilities[:5]) + (" ..." if len(self._capabilities) > 5 else ""),
            "Limits: " + "; ".join(self._limits[:3]) + (" ..." if len(self._limits) > 3 else ""),
        ]
        if self._defer_count > 0 or self._ask_user_count > 0:
            lines.append(f"Defer count (this session/life): {self._defer_count}; Ask-user count: {self._ask_user_count}.")
        out = "\n".join(lines)
        return out[:max_length] if len(out) > max_length else out

    def get_identity_narrative(self) -> str:
        return self._identity_narrative

    def set_identity_narrative(self, narrative: str) -> None:
        """Optionally update identity narrative (e.g. from operator)."""
        self._identity_narrative = (narrative or self._identity_narrative).strip()[:1000]
        self._save()
