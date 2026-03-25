"""
Moonshot pipeline: ideation -> feasibility filter -> validation design -> (optional) execution.

All goals passed to pursue_goal_with_plan are checked via rain.safety.check_goal.
Execution requires approval_callback when require_approval is True.
No new code paths bypass Rain's safety vault or autonomy limits.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from rain.config import MOONSHOT_DATA_DIR, MOONSHOT_DIVERSE_IDEATION, MOONSHOT_PARALLEL_FEASIBILITY
from rain.moonshot.memory import (
    MoonshotMemory,
    STAGE_FEASIBILITY_FAILED,
    STAGE_FEASIBILITY_PASSED,
    STAGE_IDEATED,
    STAGE_VALIDATION_DESIGNED,
)
from rain.moonshot.prompts import (
    FEASIBILITY_SYSTEM,
    IDEATION_SYSTEM,
    IDEATION_SYSTEM_DIVERSE,
    VALIDATION_SYSTEM,
    feasibility_user_prompt,
    ideation_user_prompt,
    validation_user_prompt,
)

ApprovalCallback = Callable[[int, str, str, str], bool]


def _parse_ideation_response(text: str, max_count: int) -> list[str]:
    ideas: list[str] = []
    pattern = re.compile(r"^\s*(\d+)[.)]\s*(.+?)(?=^\s*\d+[.)]\s*|\Z)", re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(text or ""):
        block = (m.group(2) or "").strip()
        if len(block) > 50 and len(ideas) < max_count:
            ideas.append(block)
    if not ideas and (text or "").strip():
        for block in re.split(r"\n\s*\n", text):
            block = block.strip()
            if len(block) > 50 and len(ideas) < max_count:
                ideas.append(block)
    return ideas[:max_count]


def _parse_feasibility_response(text: str) -> tuple[str, str]:
    t = (text or "").strip().upper()
    note = (text or "").strip()
    if "NOT_FEASIBLE" in t or "NOT FEASIBLE" in t:
        return "NOT_FEASIBLE", note[:800]
    if "FEASIBLE" in t:
        return "FEASIBLE", note[:800]
    return "NOT_FEASIBLE", "Unclear response; defaulting to NOT_FEASIBLE. " + note[:500]


def ideate(rain: Any, domain: str, count: int, past_summaries: list[str], diverse: bool | None = None) -> list[str]:
    use_diverse = diverse if diverse is not None else MOONSHOT_DIVERSE_IDEATION
    prompt = ideation_user_prompt(domain, count, past_summaries, diverse=use_diverse)
    system = IDEATION_SYSTEM_DIVERSE if use_diverse else IDEATION_SYSTEM
    # Use engine directly with correct system so think() doesn't override
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    response = rain.engine.complete(messages, temperature=0.7, max_tokens=2048)
    return _parse_ideation_response(response or "", count)


def _ideate_via_think(rain: Any, domain: str, count: int, past_summaries: list[str], diverse: bool | None = None) -> list[str]:
    """Fallback: ideate via think() when system must be set by agent."""
    prompt = ideation_user_prompt(domain, count, past_summaries, diverse=diverse if diverse is not None else MOONSHOT_DIVERSE_IDEATION)
    response = rain.think(
        prompt,
        use_tools=False,
        use_memory=False,
        history=[],
        memory_namespace=None,
    )
    return _parse_ideation_response(response or "", count)


def _safe_response(rain: Any, text: str, prompt: str = "") -> bool:
    """True if response passes safety check. Uses rain.safety.check_response when available."""
    safety = getattr(rain, "safety", None)
    if safety is None:
        return True
    check = getattr(safety, "check_response", None)
    if check is None:
        return True
    allowed, _ = check(text, prompt or None)
    return allowed


def check_feasibility(rain: Any, idea_summary: str) -> tuple[str, str]:
    prompt = feasibility_user_prompt(idea_summary)
    messages = [
        {"role": "system", "content": FEASIBILITY_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    response = rain.engine.complete(messages, temperature=0.3, max_tokens=512)
    raw = response or ""
    if not _safe_response(rain, raw, prompt):
        return "NOT_FEASIBLE", "[Safety] Feasibility output blocked."
    return _parse_feasibility_response(raw)


def design_validation(rain: Any, idea_summary: str, feasibility_note: str) -> str:
    prompt = validation_user_prompt(idea_summary, feasibility_note)
    messages = [
        {"role": "system", "content": VALIDATION_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw = (rain.engine.complete(messages, temperature=0.3, max_tokens=1024) or "").strip()
    if not _safe_response(rain, raw, prompt):
        return "[Safety] Validation output blocked."
    return raw


def run_pipeline(
    rain: Any,
    domain: str,
    max_ideas: int = 5,
    require_approval: bool = True,
    approval_callback: ApprovalCallback | None = None,
    moonshot_memory: MoonshotMemory | None = None,
    use_memory: bool = False,
) -> dict[str, Any]:
    from rain.agency.autonomous import pursue_goal_with_plan

    domain = (domain or "")[:500]
    memory = moonshot_memory or MoonshotMemory(MOONSHOT_DATA_DIR)
    past = memory.list_recent(limit=30, domain=domain)
    past_summaries = [r.get("idea_summary", "") for r in past if r.get("idea_summary")]

    ideas = ideate(rain, domain, max_ideas, past_summaries)
    if not ideas:
        return {"stage": "ideation", "domain": domain, "ideas": [], "feasible": [], "validation_plans": [], "error": "No ideas generated"}

    idea_ids: list[str] = []
    for idea in ideas:
        idea_id = memory.add(domain, idea, STAGE_IDEATED)
        idea_ids.append(idea_id)

    feasible_ideas: list[tuple[str, str, str]] = []
    if MOONSHOT_PARALLEL_FEASIBILITY and len(ideas) > 1:
        # Run feasibility checks in parallel; preserve order by index.
        index_outcomes: list[tuple[int, str, str]] = []
        with ThreadPoolExecutor(max_workers=min(len(ideas), 5)) as ex:
            fut_to_i = {ex.submit(check_feasibility, rain, idea): i for i, idea in enumerate(ideas)}
            for fut in as_completed(fut_to_i):
                i = fut_to_i[fut]
                try:
                    verdict, note = fut.result()
                    index_outcomes.append((i, verdict, note))
                except Exception:
                    index_outcomes.append((i, "NOT_FEASIBLE", "Feasibility check failed (exception)."))
        index_outcomes.sort(key=lambda x: x[0])
        for i, verdict, note in index_outcomes:
            idea = ideas[i] if i < len(ideas) else ""
            idea_id = idea_ids[i] if i < len(idea_ids) else ""
            if verdict == "FEASIBLE":
                memory.update_stage(idea_id, STAGE_FEASIBILITY_PASSED, outcome="passed", reason=note)
                feasible_ideas.append((idea, note, idea_id))
            else:
                memory.update_stage(idea_id, STAGE_FEASIBILITY_FAILED, outcome="failed", reason=note)
    else:
        for i, idea in enumerate(ideas):
            verdict, note = check_feasibility(rain, idea)
            idea_id = idea_ids[i] if i < len(idea_ids) else ""
            if verdict == "FEASIBLE":
                memory.update_stage(idea_id, STAGE_FEASIBILITY_PASSED, outcome="passed", reason=note)
                feasible_ideas.append((idea, note, idea_id))
            else:
                memory.update_stage(idea_id, STAGE_FEASIBILITY_FAILED, outcome="failed", reason=note)

    validation_plans: list[dict[str, Any]] = []
    for idea, feas_note, idea_id in feasible_ideas:
        plan_text = design_validation(rain, idea, feas_note)
        memory.update_stage(idea_id, STAGE_VALIDATION_DESIGNED, outcome="designed", reason=plan_text[:500])
        validation_plans.append({
            "idea_id": idea_id,
            "idea_summary": idea[:500],
            "validation_plan": plan_text,
        })

    result: dict[str, Any] = {
        "stage": "validation_designed",
        "domain": domain,
        "ideas": ideas,
        "feasible": [t[0] for t in feasible_ideas],
        "validation_plans": validation_plans,
    }
    if require_approval and approval_callback and validation_plans:
        result["execution_available"] = True
        result["execution_note"] = "To run a validation step, call pursue_goal_with_plan with the desired goal and this approval_callback."
    return result
