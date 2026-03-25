"""Deterministic Reasoning Orchestrator (Conscience Gate).

The LLM proposes a draft plan (DAG/steps); it is not executable until this
deterministic module validates every step against HARD_FORBIDDEN and produces
the executable task graph. Ensures that even if the LLM is tricked or jailbroken,
the execution engine cannot physically run an unsafe step.

Vocal Gate: optional check that high-risk commands may only be executed when
the current speaker is in the allowed set (voice-verified identity).
"""

from __future__ import annotations

from typing import Any, Callable


# Actions that require Vocal Gate when allowed_speakers is set (e.g. transfer, delete, deploy)
VOCAL_GATE_HIGH_RISK_KEYWORDS = [
    "transfer", "delete", "remove", "drop", "overwrite", "deploy", "execute code",
    "run code", "shell", "funds", "payment", "credit", "server", "database",
]


def _is_high_risk_action(action: str) -> bool:
    """True if the step touches money, deletion, or code execution."""
    lower = action.lower()
    return any(kw in lower for kw in VOCAL_GATE_HIGH_RISK_KEYWORDS)


def vocal_gate_check(
    current_speaker: str | None,
    allowed_speakers: set[str] | None,
    steps: list[dict[str, Any]],
) -> tuple[bool, str]:
    """
    If allowed_speakers is set and current_speaker is not in it, and any step is high-risk,
    return (False, reason). Otherwise (True, "").
    When allowed_speakers is None or empty, Vocal Gate is disabled.
    """
    if not allowed_speakers or current_speaker is None:
        return True, ""
    if current_speaker in allowed_speakers:
        return True, ""
    for step in steps:
        action = str(step.get("action", "")).strip()
        if action and _is_high_risk_action(action):
            return False, f"Vocal Gate: high-risk action requires authorized speaker. Current speaker: {current_speaker!r}; allowed: {sorted(allowed_speakers)}."
    return True, ""


def validate_plan(
    steps: list[dict[str, Any]],
    safety_check: Callable[[str, str], tuple[bool, str]],
) -> list[dict[str, Any]]:
    """
    Validate each step against the safety check (HARD_FORBIDDEN, etc.).
    Returns only steps that pass. Pure deterministic code — no LLM.
    Call vocal_gate_check(current_speaker, allowed_speakers, steps) before this when using voice.
    """
    if not steps:
        return []
    safe = []
    for step in steps:
        action = str(step.get("action", "")).strip()
        if not action:
            continue
        allowed, _ = safety_check(action, action)
        if allowed:
            safe.append(step)
    return safe


def verify_step_execution(step_action: str, response_text: str) -> tuple[bool, str]:
    """
    Verify that the execution result is consistent with a successful step.
    Returns (ok, note). ok=False when response indicates block, error, or failure.
    Used for step-level verification in the autonomous loop.
    """
    if not response_text or not response_text.strip():
        return False, "Empty response"
    r = response_text.strip()
    if r.startswith("[Safety]") or r.startswith("[Escalation]") or r.startswith("[Grounding]") or r.startswith("[Defer]"):
        return False, r[:200]
    # Only treat "Error:" as tool-style failure when response is short (avoid blocking explanatory text)
    if (r.startswith("Error:") or r.startswith("Error ")) and len(r) < 500:
        return False, r[:200]
    if r.startswith("[Conscience Gate]") or r.startswith("[Vocal Gate]"):
        return False, r[:200]
    return True, ""
