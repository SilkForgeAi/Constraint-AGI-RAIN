"""World model simulator — hypothetical "what if" reasoning. No real action.

SAFETY: This module is for reasoning only. It never executes actions.
All simulations are hypothetical. The LLM predicts outcomes; nothing is done.

World model 10/10 (within Rain design): explicit state schema, stateful rollout,
ontology-enforced consistency (coherent_model), entity lifecycle, strict confidence
on failure, and planner integration. No learned dynamics; no autonomy or self-improvement.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from rain.core.engine import CoreEngine
from rain.world.coherent_model import check_state_consistency as coherent_consistency

# Max steps for multi-step rollout (safety cap)
MAX_ROLLOUT_STEPS = 5

# Structured state schema: entities (id -> {type, exists, attrs}), facts, summary
# Used for stateful transition so each step sees previous step's output state.
def make_initial_state(goal: str = "", context: str = "") -> dict[str, Any]:
    """Build initial world state from goal/context for rollout. No real-world state."""
    return {
        "entities": {},
        "facts": [],
        "summary": goal[:500] if goal else "No goal yet.",
        "_context": context[:800] if context else "",
    }


def validate_consistency(
    prev_state: dict[str, Any],
    next_state: dict[str, Any],
    action: str,
) -> tuple[bool, str]:
    """
    Schema and entity lifecycle consistency. Next state must have required keys;
    entities that existed in prev must either persist or be explicitly deleted in next.
    Returns (ok, message).
    """
    if not isinstance(next_state, dict):
        return False, "next_state must be a dict"
    if "summary" not in next_state and "facts" not in next_state and "entities" not in next_state:
        return False, "next_state missing summary/facts/entities"
    # Entity lifecycle: when both sides have entity records, prev entities with exists=True must appear in next
    prev_entities = prev_state.get("entities") or {}
    next_entities = next_state.get("entities") or {}
    if isinstance(prev_entities, dict) and isinstance(next_entities, dict) and len(next_entities) > 0:
        for eid, pval in prev_entities.items():
            if isinstance(pval, dict) and pval.get("exists", True) is True:
                if eid not in next_entities:
                    return False, "entity_lifecycle: entity disappeared without explicit deletion"
    return True, "ok"


HYPOTHETICAL_PROMPT = """You are reasoning about hypothetical scenarios. No actions are executed.
Given the current state and a proposed action, predict what might happen.
Output a brief prediction. Stay grounded. If uncertain, say so.
Do not claim certainty. Use "might", "could", "likely" where appropriate."""

STRUCTURED_SIM_PROMPT = """You are simulating a hypothetical scenario. No actions are executed.
Given the current state and a proposed action, predict what might happen.

Respond with JSON only, in this exact format (no other text):
{"outcome": "brief description of what might happen", "confidence": "high" or "medium" or "low", "key_change": "one sentence: what is the main change from current state"}

If you cannot produce valid JSON, respond with plain text only (no JSON)."""

TRANSITION_PROMPT = """You are a world model. Given the current state (JSON) and an action, output the next state after the action (hypothetical; nothing is executed).

Ontology: reason with physics-like consistency (object persistence, cause before effect) and folk psychology (beliefs and goals affect actions). Keep predictions consistent across steps. If an entity is removed by the action, set that entity to {{"exists": false}} in next_state.entities; do not drop entities without marking deletion.

Current state (JSON):
{state_json}

Action (hypothetical): {action}

Output ONLY valid JSON in this exact format (no other text):
{{"next_state": {{"entities": {{}}, "facts": [], "summary": "one sentence summary of situation after action"}}, "confidence": "high" or "medium" or "low", "key_change": "one sentence: main change"}}

Keep entities and facts minimal. summary must reflect the outcome. confidence reflects your certainty."""


def _classical_transition(state: dict[str, Any], action: str, context: str = "") -> tuple[dict[str, Any], str]:
    """
    Deterministic classical backend: no LLM. Produces next state from rule-based update.
    Use when RAIN_WORLD_MODEL_BACKEND=classical for reproducible demos or when plugging in learned/physics sims elsewhere.
    """
    summary = (state.get("summary") or "").strip()
    action = (action or "").strip()
    next_summary = f"After action '{action[:80]}': {summary[:200]}." if summary else f"Action done: {action[:80]}."
    next_state = {
        "entities": state.get("entities") or {},
        "facts": state.get("facts") or [],
        "summary": next_summary[:500],
        "_context": (context or state.get("_context") or "")[:800],
    }
    return next_state, "high"


class WorldSimulator:
    """Hypothetical scenario simulation. Reasoning only — never executes.
    Supports structured state and stateful rollout for planner lookahead.
    Pluggable backend: llm (default), classical (deterministic), or external (set via set_external_backend).
    """

    def __init__(self, engine: CoreEngine | None = None):
        self.engine = engine or CoreEngine()
        self._external_transition: Callable[[dict, str, str], tuple[dict, str]] | None = None

    def set_external_backend(self, transition_fn: Callable[[dict[str, Any], str, str], tuple[dict[str, Any], str]]) -> None:
        """Plug in a learned world model or physics simulator: (state, action, context) -> (next_state, confidence)."""
        self._external_transition = transition_fn

    def _parse_transition_response(self, raw: str) -> dict | None:
        """Parse LLM output for transition: next_state, confidence, key_change."""
        raw = raw.strip()
        start = raw.find("{")
        if start < 0:
            return None
        depth = 0
        for i, c in enumerate(raw[start:], start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(raw[start : i + 1])
                        if isinstance(obj, dict) and "next_state" in obj:
                            ns = obj["next_state"]
                            if isinstance(ns, dict):
                                return {
                                    "next_state": {
                                        "entities": ns.get("entities", {}),
                                        "facts": ns.get("facts", []),
                                        "summary": str(ns.get("summary", "")),
                                        "_context": ns.get("_context", ""),
                                    },
                                    "confidence": str(obj.get("confidence", "medium")).lower()[:6],
                                    "key_change": str(obj.get("key_change", "")),
                                }
                    except json.JSONDecodeError:
                        pass
                    break
        return None

    def transition(
        self,
        state: dict[str, Any],
        action: str,
        context: str = "",
    ) -> tuple[dict[str, Any], str]:
        """
        Structured (state, action) -> (next_state, confidence). No real execution.
        state and next_state follow the shared schema (entities, facts, summary).
        Uses pluggable backend: classical (deterministic), external (if set), or LLM.
        """
        try:
            from rain import config
            backend = getattr(config, "WORLD_MODEL_BACKEND", "llm")
        except Exception:
            backend = "llm"
        if backend == "classical":
            return _classical_transition(state, action, context)
        if self._external_transition is not None:
            return self._external_transition(state, action, context)
        state_json = json.dumps(state, default=str)
        prompt = TRANSITION_PROMPT.format(state_json=state_json, action=action)
        raw = self.engine.complete(
            [
                {"role": "system", "content": "Output only valid JSON. No markdown, no explanation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        ).strip()
        parsed = self._parse_transition_response(raw)
        if parsed:
            next_state = parsed["next_state"]
            if context and "_context" not in next_state:
                next_state["_context"] = context[:800]
            ok, msg = validate_consistency(state, next_state, action)
            if not ok:
                next_state["summary"] = (next_state.get("summary") or "") + f" [consistency: {msg}]"
            ok2, msg2 = coherent_consistency(next_state, state, action)
            if not ok2:
                next_state["summary"] = (next_state.get("summary") or "") + f" [ontology: {msg2}]"
            confidence = parsed["confidence"]
            if not ok or not ok2:
                confidence = "low"
            return next_state, confidence
        # Fallback: use make_initial_state with summary from key_change or raw
        fallback = make_initial_state(goal=raw[:400], context=context)
        return fallback, "low"

    def rollout_stateful(
        self,
        initial_state: dict[str, Any],
        actions: list[str],
        context: str = "",
        max_steps: int = MAX_ROLLOUT_STEPS,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Multi-step rollout threading state: s0 -> a1 -> s1 -> a2 -> s2 ...
        Returns (trajectory, overall_confidence). trajectory items: {state, action, next_state, confidence}.
        overall_confidence is the minimum step confidence (pessimistic).
        """
        trajectory: list[dict[str, Any]] = []
        actions = actions[:max_steps]
        confidences: list[str] = []
        state = dict(initial_state)
        for action in actions:
            if not action or not str(action).strip():
                continue
            next_state, confidence = self.transition(state, str(action).strip(), context=context)
            trajectory.append({
                "state": state,
                "action": action,
                "next_state": next_state,
                "confidence": confidence,
            })
            confidences.append(confidence)
            state = next_state
        # overall = min confidence (high=3, medium=2, low=1)
        order = {"high": 3, "medium": 2, "low": 1}
        overall = "high"
        if confidences:
            min_val = min(order.get(c, 0) for c in confidences)
            for k, v in order.items():
                if v == min_val:
                    overall = k
                    break
        return trajectory, overall

    def _parse_structured(self, raw: str) -> dict | None:
        """Try to extract JSON from LLM output. Returns dict with outcome, confidence, key_change or None."""
        raw = raw.strip()
        # Try raw JSON
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "outcome" in obj:
                return {
                    "outcome": str(obj.get("outcome", "")),
                    "confidence": str(obj.get("confidence", "medium")).lower()[:6],
                    "key_change": str(obj.get("key_change", "")),
                }
        except json.JSONDecodeError:
            pass
        # Try to find JSON block
        start = raw.find("{")
        if start >= 0:
            depth = 0
            for i, c in enumerate(raw[start:], start):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(raw[start : i + 1])
                            if isinstance(obj, dict) and "outcome" in obj:
                                return {
                                    "outcome": str(obj.get("outcome", "")),
                                    "confidence": str(obj.get("confidence", "medium")).lower()[:6],
                                    "key_change": str(obj.get("key_change", "")),
                                }
                        except json.JSONDecodeError:
                            pass
                        break
        return None

    def simulate(self, state: str, action: str, context: str = "") -> str:
        """
        Predict what might happen if action were taken in state. Hypothetical only.
        Returns prediction text (structured when possible). Nothing is executed.
        """
        prompt = f"""State: {state}
Proposed action (hypothetical): {action}
{f'Context: {context}' if context else ''}

What might happen? (This is a simulation. No real action.)"""
        raw = self.engine.complete(
            [
                {"role": "system", "content": HYPOTHETICAL_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        ).strip()
        return raw

    def simulate_structured(self, state: str, action: str, context: str = "") -> tuple[str, dict | None]:
        """
        Same as simulate but asks for JSON. Returns (display_string, parsed_dict or None).
        Parsed dict has outcome, confidence, key_change. Used by rollout.
        """
        prompt = f"""State: {state}
Proposed action (hypothetical): {action}
{f'Context: {context}' if context else ''}

Respond with JSON: {{"outcome": "...", "confidence": "high|medium|low", "key_change": "..."}}"""
        raw = self.engine.complete(
            [
                {"role": "system", "content": STRUCTURED_SIM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        ).strip()
        parsed = self._parse_structured(raw)
        if parsed:
            display = f"Outcome: {parsed['outcome']}\nConfidence: {parsed['confidence']}\nKey change: {parsed['key_change']}"
            return display, parsed
        return raw, None

    def simulate_rollout(self, state: str, actions: str, context: str = "", max_steps: int = MAX_ROLLOUT_STEPS) -> str:
        """
        Multi-step hypothetical rollout: state + action_1 -> outcome_1; then outcome_1 as state + action_2 -> ...
        actions: semicolon-separated list of actions (e.g. "launch campaign; measure conversions; iterate").
        Returns a combined narrative. Cap at max_steps. No real actions.
        """
        action_list = [a.strip() for a in actions.split(";") if a.strip()][:max_steps]
        if not action_list:
            return "No actions provided. Give a semicolon-separated list of hypothetical actions."
        steps = []
        current_state = state
        for i, action in enumerate(action_list, 1):
            display, parsed = self.simulate_structured(current_state, action, context=context)
            steps.append(f"Step {i} (action: {action}):\n{display}")
            if parsed:
                # Use key_change or outcome as the new state for next step
                next_state = parsed.get("key_change") or parsed.get("outcome") or current_state
                current_state = next_state
            else:
                # Unstructured fallback: use last line or full output as next state
                current_state = display[-300:] if len(display) > 300 else display
        return "\n\n".join(steps)
