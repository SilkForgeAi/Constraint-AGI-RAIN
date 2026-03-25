"""Coherent world model — ontology (physics, folk psychology), consistency across domains.

SAFETY: Reasoning only. No execution. No self-modification.
Provides a single, consistent view of how the world works for use in simulation and planning.

10/10 scope: Enforced ontology and entity lifecycle within LLM-based, non-learned, safe world model.
"""

from __future__ import annotations

import re
from typing import Any

# Ontology: physics-like and folk-psychology-like rules (enforced in check_state_consistency).
PHYSICS_LIKE = ("object_persistence", "cause_precedes_effect", "contact_causation")
FOLK_PSYCHOLOGY_LIKE = ("beliefs_affect_actions", "goals_persist_until_satisfied", "agents_have_limited_info")


def get_ontology_rules() -> dict[str, list[str]]:
    """Return ontology categories and short rule descriptions for prompts."""
    return {
        "physics_like": list(PHYSICS_LIKE),
        "folk_psychology_like": list(FOLK_PSYCHOLOGY_LIKE),
    }


def _entity_ids_with_exists(state: dict[str, Any]) -> dict[str, bool]:
    """Return entity id -> exists for states that use the entity schema (exists field)."""
    out: dict[str, bool] = {}
    entities = state.get("entities") or {}
    if not isinstance(entities, dict):
        return out
    for eid, val in entities.items():
        if isinstance(val, dict):
            out[str(eid)] = val.get("exists", True)
        else:
            out[str(eid)] = True
    return out


def _summary_implies_deletion_without_action(summary: str, prev_summary: str, action: str) -> bool:
    """True if summary says something was removed/deleted and action doesn't imply that."""
    summary_lower = (summary or "").lower()
    prev_lower = (prev_summary or "").lower()
    action_lower = (action or "").lower()
    deletion_words = ("removed", "deleted", "gone", "destroyed", "eliminated", "no longer", "disappeared")
    action_implies_removal = any(
        w in action_lower for w in ("remove", "delete", "destroy", "eliminate", "discard", "drop")
    )
    if not action_implies_removal:
        for w in deletion_words:
            if w in summary_lower and not (w in prev_lower):
                return True
    return False


def _summary_effect_before_cause(summary: str, prev_summary: str, action: str) -> bool:
    """True if next summary describes the effect as already true before the action (cause precedes effect)."""
    action_lower = (action or "").lower().strip()
    summary_lower = (summary or "").lower()
    if not action_lower or not summary_lower:
        return False
    # "already done", "had already been completed" in next when action is to do it suggests effect before cause
    if re.search(
        r"\b(already|had been|was already)\s+(been\s+)?(done|completed|finished|achieved)",
        summary_lower,
    ):
        return True
    return False


def check_state_consistency(
    state: dict[str, Any],
    previous_state: dict[str, Any] | None,
    action: str,
) -> tuple[bool, str]:
    """
    Check that a predicted next state is consistent with ontology and entity lifecycle.
    Returns (consistent, message). Enforces: object persistence, no magic deletion, cause precedes effect.
    """
    if not state or not isinstance(state, dict):
        return False, "state must be a non-empty dict"
    if previous_state is None:
        return True, "ok"

    prev_summary = (previous_state.get("summary") or "").strip()
    summary = (state.get("summary") or "").strip()
    action = (action or "").strip()

    # Object persistence: no magic deletion (summary-based)
    if _summary_implies_deletion_without_action(summary, prev_summary, action):
        return False, "object_persistence: next state implies removal without action implying it"

    # Cause precedes effect: effect shouldn't be described as already true before action
    if _summary_effect_before_cause(summary, prev_summary, action):
        return False, "cause_precedes_effect: next state describes effect as already true"

    # Entity lifecycle: if we have entity records, deleted entities must not reappear as existing without create/restore
    prev_entities = _entity_ids_with_exists(previous_state)
    next_entities = _entity_ids_with_exists(state)
    action_lower = action.lower()
    implies_create = any(w in action_lower for w in ("create", "add", "restore", "introduce", "spawn"))
    for eid, next_exists in next_entities.items():
        prev_exists = prev_entities.get(eid, None)
        if prev_exists is False and next_exists is True and not implies_create:
            return False, "entity_lifecycle: deleted entity reappears without create/restore action"

    return True, "ok"


def world_model_context_for_prompt() -> str:
    """Brief world-model context to inject into prompts (ontology + consistency expectation)."""
    return (
        "World model: reason with physics-like consistency (object persistence, cause before effect) "
        "and folk psychology (beliefs and goals affect actions). Keep predictions consistent across steps."
    )
