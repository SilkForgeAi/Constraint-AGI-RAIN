"""
Pre-LLM system prompt injections: session/task world, GI stack, Router v2.
"""

from __future__ import annotations

from typing import Any


def apply_pre_llm_system(
    agent: Any,
    system: str,
    prompt: str,
    *,
    use_tools: bool,
    use_memory: bool,
    safety_allowed: bool,
) -> str:
    try:
        from rain.config import GI_STACK_ENABLED, ROUTER_V2_ENABLED, SESSION_TASK_WORLD_ENABLED
    except Exception:
        GI_STACK_ENABLED = False
        ROUTER_V2_ENABLED = False
        SESSION_TASK_WORLD_ENABLED = True

    if SESSION_TASK_WORLD_ENABLED:
        from rain.world.session_task_state import session_task_fragment_for_prompt
        from rain.world.session_task_state import update_session_task_from_prompt

        update_session_task_from_prompt(agent, prompt)
        system = session_task_fragment_for_prompt(agent, system, prompt)

    if GI_STACK_ENABLED:
        from rain.integration.gi_hooks import maybe_apply_gi_stack
        from rain.world.session_task_state import update_session_task_from_prompt

        system, gi = maybe_apply_gi_stack(
            system,
            prompt,
            use_tools=use_tools,
            use_memory=use_memory,
            safety_allowed=safety_allowed,
            audit=getattr(agent, "audit", None),
        )
        agent._gi_orchestration_state = gi
        if gi is not None:
            update_session_task_from_prompt(agent, prompt, gi_mode=gi.mode.value)
    else:
        agent._gi_orchestration_state = None

    if ROUTER_V2_ENABLED and getattr(agent, "_gi_orchestration_state", None) is not None:
        from rain.cognition.router_v2 import RouterV2

        system = RouterV2.apply_system_addon(system, prompt, agent._gi_orchestration_state)

    return system
