"""
Classical Predicate Backend — deterministic, LLM-free world model.

Replaces the stub in simulator.py that just appended strings.

How it works:
  - Maintains a structured predicate store: {entity_id: {attr: value, exists: bool}}
  - A rule engine parses action strings into one or more predicate operations
  - Operations fire deterministically — same input always produces same output
  - Returns a fully structured next_state in the Rain world model schema

Why this matters for constraint AGI:
  - The LLM proposes actions; the classical backend evaluates their structural
    consequences without calling the LLM again. Ground truth is code, not text.
  - Auditable: every state transition is a Python dict diff, not a string.
  - Plugged in via RAIN_WORLD_MODEL_BACKEND=classical in .env

Rule coverage:
  create/add/spawn/introduce     → entity appears with exists=True
  delete/remove/destroy/purge    → entity exists=False
  enable/activate/start/open     → entity.status=active
  disable/deactivate/stop/close  → entity.status=inactive
  transfer/move/send X to Y      → entity.location=Y
  update/set/change X to/= Y     → entity.value=Y (or matched attr)
  connect/link X to Y            → entity.connected_to=Y
  observe/read/fetch/get X       → no state change (read-only)
  unknown action                 → fact appended, confidence=medium
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


# ── Operation types ────────────────────────────────────────────────────────────

@dataclass
class PredicateOp:
    """A single deterministic state update."""
    op: str          # create | delete | update_attr | append_fact | no_change
    entity: str      # entity ID / name (lowercased)
    attr: str = ""   # attribute name (for update_attr)
    value: Any = ""  # new value


# ── Rule patterns ─────────────────────────────────────────────────────────────

# Each rule: (compiled_regex, op_type, attr_name or "")
# Group 1 = entity, Group 2 = value (optional)
_RULES: list[tuple[re.Pattern, str, str]] = [
    # create
    (re.compile(r"(?:create|add|spawn|introduce|instantiate|register|deploy)\s+(?:a\s+|an\s+|the\s+)?(.+?)(?:\s+(?:with|in|at|to|into|as)\b.*)?$", re.I), "create", ""),
    # delete
    (re.compile(r"(?:delete|remove|destroy|drop|purge|wipe|terminate|decommission|unregister)\s+(?:a\s+|an\s+|the\s+)?(.+?)(?:\s+(?:from|in|at)\b.*)?$", re.I), "delete", ""),
    # enable
    (re.compile(r"(?:enable|activate|start|open|turn\s+on|launch|resume|begin)\s+(?:a\s+|an\s+|the\s+)?(.+)", re.I), "update_attr", "status:active"),
    # disable
    (re.compile(r"(?:disable|deactivate|stop|close|turn\s+off|pause|suspend|halt)\s+(?:a\s+|an\s+|the\s+)?(.+)", re.I), "update_attr", "status:inactive"),
    # transfer / move X to Y
    (re.compile(r"(?:transfer|move|send|migrate|relocate)\s+(?:a\s+|an\s+|the\s+)?(.+?)\s+(?:to|into|from)\s+(.+)", re.I), "update_attr", "location"),
    # connect X to Y
    (re.compile(r"(?:connect|link|attach|associate|bind)\s+(?:a\s+|an\s+|the\s+)?(.+?)\s+(?:to|with)\s+(.+)", re.I), "update_attr", "connected_to"),
    # update / set X to Y
    (re.compile(r"(?:update|set|change|modify|assign)\s+(?:a\s+|an\s+|the\s+)?(.+?)\s+(?:to|=|:)\s+(.+)", re.I), "update_attr", "value"),
    # observe / read / fetch (read-only — no state change)
    (re.compile(r"(?:observe|read|fetch|get|retrieve|check|query|inspect|monitor|measure)\s+(?:a\s+|an\s+|the\s+)?(.+)", re.I), "no_change", ""),
    # execute / run step (generic — append fact only)
    (re.compile(r"(?:execute|run|perform|apply|process|complete|finish)\s+(.+)", re.I), "append_fact", ""),
]


# Common role/type prefixes that are noise when matching existing entities
_ROLE_PREFIXES = re.compile(
    r"^(user|users|service|services|agent|agents|node|nodes|process|processes|"
    r"system|systems|device|devices|resource|resources|record|records|entry|entries)\s+",
    re.I,
)


def _parse_entity(raw: str) -> str:
    """Normalise entity name: lowercase, strip articles/punctuation and role prefixes."""
    s = raw.strip().rstrip(".,;:")
    s = re.sub(r"^(a|an|the)\s+", "", s, flags=re.I)
    # Strip common role prefixes so "user alice" and "alice" resolve to the same entity
    s = _ROLE_PREFIXES.sub("", s).strip()
    return s.lower()[:80]


def _match_rules(action: str) -> PredicateOp:
    """Try each rule in order; return the first match. Unknown actions → append_fact."""
    a = action.strip()
    for pattern, op, attr_spec in _RULES:
        m = pattern.fullmatch(a) or pattern.match(a)
        if m:
            entity = _parse_entity(m.group(1) if m.lastindex and m.lastindex >= 1 else a)
            value = ""
            attr = attr_spec
            # attr_spec may be "status:active" or a bare attr name needing group 2
            if ":" in attr_spec:
                attr, value = attr_spec.split(":", 1)
            elif attr_spec and m.lastindex and m.lastindex >= 2:
                value = _parse_entity(m.group(2))
            return PredicateOp(op=op, entity=entity, attr=attr, value=value)
    # Unknown — just log as fact
    return PredicateOp(op="append_fact", entity="", attr="", value=action[:120])


# ── State helpers ─────────────────────────────────────────────────────────────

def _apply_op(op: PredicateOp, entities: dict[str, dict], facts: list[str]) -> tuple[dict, list]:
    """Apply one PredicateOp to entities+facts. Returns (new_entities, new_facts). Pure."""
    entities = deepcopy(entities)
    facts = list(facts)

    if op.op == "create":
        if op.entity and op.entity not in entities:
            entities[op.entity] = {"exists": True, "status": "created"}
        elif op.entity:
            entities[op.entity]["exists"] = True
            entities[op.entity]["status"] = "re-created"

    elif op.op == "delete":
        if op.entity in entities:
            entities[op.entity]["exists"] = False
            entities[op.entity]["status"] = "deleted"
        else:
            # Entity didn't exist in state — note it as a fact anyway
            facts.append(f"attempted delete of unknown entity: {op.entity}")

    elif op.op == "update_attr":
        if op.entity not in entities:
            entities[op.entity] = {"exists": True}
        if op.attr:
            entities[op.entity][op.attr] = op.value

    elif op.op == "append_fact":
        v = str(op.value or "").strip()
        if v and v not in facts:
            facts.append(v)
            if len(facts) > 30:
                facts.pop(0)

    # no_change: pass through

    return entities, facts


def _build_summary(action: str, entities: dict[str, dict], facts: list[str]) -> str:
    """Build a human-readable summary of the current state."""
    active = [e for e, v in entities.items() if isinstance(v, dict) and v.get("exists", True)]
    deleted = [e for e, v in entities.items() if isinstance(v, dict) and not v.get("exists", True)]
    parts = []
    if active:
        parts.append(f"Active: {', '.join(sorted(active)[:6])}")
    if deleted:
        parts.append(f"Deleted: {', '.join(sorted(deleted)[:4])}")
    if facts:
        parts.append(f"Recent: {facts[-1][:80]}")
    base = "; ".join(parts) if parts else "Empty world state."
    return f"[classical] After '{action[:60]}': {base}"[:500]


# ── Public API ────────────────────────────────────────────────────────────────

class ClassicalPredicateBackend:
    """
    Deterministic, LLM-free world model backend.

    Usage:
        backend = ClassicalPredicateBackend()
        next_state, confidence = backend.transition(state, action)

    Or via the pluggable hook:
        simulator.set_external_backend(ClassicalPredicateBackend().transition)
    """

    def __init__(self) -> None:
        # Internal audit log of applied ops (for debugging/verification)
        self._op_log: list[dict] = []

    def transition(
        self,
        state: dict[str, Any],
        action: str,
        context: str = "",
    ) -> tuple[dict[str, Any], str]:
        """
        (state, action, context) → (next_state, confidence).

        Deterministic. No LLM. Same inputs always produce the same output.
        confidence = "high" when a known rule matched; "medium" for unknown actions.
        """
        action = (action or "").strip()
        if not action:
            return dict(state), "high"

        entities = deepcopy(state.get("entities") or {})
        facts = list(state.get("facts") or [])

        # Parse action into predicate operation
        op = _match_rules(action)

        # Apply operation
        entities, facts = _apply_op(op, entities, facts)

        # Build summary
        summary = _build_summary(action, entities, facts)

        next_state = {
            "entities": entities,
            "facts": facts,
            "summary": summary,
            "_context": (context or state.get("_context", ""))[:800],
            "_op": {"type": op.op, "entity": op.entity, "attr": op.attr, "value": str(op.value)[:60]},
        }

        confidence = "high" if op.op != "append_fact" else "medium"

        # Audit log (bounded)
        self._op_log.append({"action": action[:80], "op": op.op, "entity": op.entity})
        if len(self._op_log) > 200:
            self._op_log.pop(0)

        return next_state, confidence

    def get_op_log(self) -> list[dict]:
        """Return recent operation log (for audit/debugging)."""
        return list(self._op_log)

    def get_entity_state(self, state: dict[str, Any], entity: str) -> dict | None:
        """Query a specific entity's current attributes from a state dict."""
        return (state.get("entities") or {}).get(entity.lower())

    def list_active_entities(self, state: dict[str, Any]) -> list[str]:
        """Return names of entities currently marked as existing."""
        return [
            e for e, v in (state.get("entities") or {}).items()
            if isinstance(v, dict) and v.get("exists", True)
        ]


# Singleton for use when RAIN_WORLD_MODEL_BACKEND=classical
_singleton: ClassicalPredicateBackend | None = None


def get_classical_backend() -> ClassicalPredicateBackend:
    global _singleton
    if _singleton is None:
        _singleton = ClassicalPredicateBackend()
    return _singleton
