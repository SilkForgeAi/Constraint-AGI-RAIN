"""GI stack hooks for cognitive_inject — epistemic mode + system addon."""

from __future__ import annotations

from typing import Any

from rain.cognition.gi_stack import GIOrchestrationState, decide_epistemic_mode, gi_system_addon


def maybe_apply_gi_stack(
    system: str,
    prompt: str,
    *,
    use_tools: bool,
    use_memory: bool,
    safety_allowed: bool,
    audit: Any = None,
) -> tuple[str, GIOrchestrationState | None]:
    """Append GI orchestration block to system when safety allows; log mode to audit if present."""
    gi = decide_epistemic_mode(
        prompt,
        use_tools=use_tools,
        use_memory=use_memory,
        safety_blocked=not safety_allowed,
    )
    out = system + gi_system_addon(prompt, gi)
    if audit is not None:
        try:
            audit.log(
                "gi_stack",
                {"mode": gi.mode.value, "complexity": gi.prompt_complexity, "reasons": gi.reasons[:5]},
                outcome="ok",
            )
        except Exception:
            pass
    return out, gi
