"""Causal Dependency Graph — deterministic, zero LLM.

A directed acyclic graph (DAG) where nodes are entities/variables and
edges represent causal influence: A --[strength]--> B means "A causally
affects B".  Used by causal_inference.py for proper counterfactual
reasoning instead of just parallel keyword-scored simulations.

Key operations
--------------
- build_graph_from_actions(actions, states): infer edges from plan steps
- what_if_remove(node_id): set of nodes transitively affected by removing node_id
- counterfactual_impact(cause, target): True if cause is on any causal path to target
- transitive_risk(node_id): max risk of anything downstream of node_id
- shortest_causal_path(cause, target): list of node IDs, empty if no path

Design: plain Python, no external deps, fully serialisable to JSON.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Node and edge
# ---------------------------------------------------------------------------

@dataclass
class CausalNode:
    """A variable or entity in the causal graph."""
    id: str
    label: str = ""
    # Prior risk for this node (0–1). Typically set from safety vault scoring.
    risk_prior: float = 0.2
    # Additional metadata (type, source, etc.)
    meta: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CausalNode) and self.id == other.id


@dataclass
class CausalEdge:
    """A directed causal influence: cause_id --[strength]--> effect_id."""
    cause_id: str
    effect_id: str
    # Strength of causal influence [0, 1].  1.0 = deterministic; <0.5 = weak.
    strength: float = 0.8
    # Free-text description (e.g. "deleting X causes Y to fail")
    description: str = ""


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class CausalGraph:
    """
    Directed acyclic causal dependency graph.

    Invariants enforced at `add_edge`:
    - No self-loops (A -> A).
    - Adding an edge that would create a cycle raises CyclicCausalError.
    """

    def __init__(self) -> None:
        # node_id -> CausalNode
        self._nodes: dict[str, CausalNode] = {}
        # cause_id -> list[CausalEdge]
        self._out: dict[str, list[CausalEdge]] = {}
        # effect_id -> list[CausalEdge]
        self._in: dict[str, list[CausalEdge]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(
        self,
        node_id: str,
        label: str = "",
        risk_prior: float = 0.2,
        meta: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> CausalNode:
        """Add or retrieve a node. If overwrite=True, replaces existing node."""
        if node_id not in self._nodes or overwrite:
            self._nodes[node_id] = CausalNode(
                id=node_id,
                label=label or node_id,
                risk_prior=max(0.0, min(1.0, risk_prior)),
                meta=meta or {},
            )
            if node_id not in self._out:
                self._out[node_id] = []
            if node_id not in self._in:
                self._in[node_id] = []
        return self._nodes[node_id]

    def add_edge(
        self,
        cause_id: str,
        effect_id: str,
        strength: float = 0.8,
        description: str = "",
    ) -> None:
        """
        Add a causal edge cause_id -> effect_id.
        Auto-creates missing nodes. Raises CyclicCausalError if the edge would create a cycle.
        """
        if cause_id == effect_id:
            return  # silently ignore self-loops

        # Auto-create nodes if absent.
        self.add_node(cause_id)
        self.add_node(effect_id)

        # Cycle check: would adding this edge make effect_id reachable from itself?
        if self._is_reachable(effect_id, cause_id):
            raise CyclicCausalError(
                f"Adding {cause_id} -> {effect_id} would create a cycle "
                f"(path {effect_id} -> ... -> {cause_id} already exists)."
            )

        # Deduplicate: if the edge already exists, update strength if stronger.
        for existing in self._out.get(cause_id, []):
            if existing.effect_id == effect_id:
                if strength > existing.strength:
                    existing.strength = strength
                return

        edge = CausalEdge(cause_id=cause_id, effect_id=effect_id, strength=strength, description=description)
        self._out.setdefault(cause_id, []).append(edge)
        self._in.setdefault(effect_id, []).append(edge)

    # ------------------------------------------------------------------
    # Traversal helpers
    # ------------------------------------------------------------------

    def _is_reachable(self, source: str, target: str) -> bool:
        """BFS/DFS: True if target is reachable from source following out-edges."""
        if source == target:
            return True
        visited: set[str] = set()
        stack = [source]
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in visited:
                continue
            visited.add(node)
            for edge in self._out.get(node, []):
                stack.append(edge.effect_id)
        return False

    def children_of(self, node_id: str) -> list[str]:
        """Direct causal successors of node_id."""
        return [e.effect_id for e in self._out.get(node_id, [])]

    def parents_of(self, node_id: str) -> list[str]:
        """Direct causal predecessors of node_id."""
        return [e.cause_id for e in self._in.get(node_id, [])]

    def descendants_of(self, node_id: str) -> set[str]:
        """All nodes transitively reachable from node_id (i.e. causally downstream)."""
        visited: set[str] = set()
        stack = [node_id]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            for edge in self._out.get(n, []):
                stack.append(edge.effect_id)
        visited.discard(node_id)
        return visited

    def ancestors_of(self, node_id: str) -> set[str]:
        """All nodes from which node_id is causally reachable."""
        visited: set[str] = set()
        stack = [node_id]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            for edge in self._in.get(n, []):
                stack.append(edge.cause_id)
        visited.discard(node_id)
        return visited

    # ------------------------------------------------------------------
    # Counterfactual queries
    # ------------------------------------------------------------------

    def what_if_remove(self, node_id: str) -> set[str]:
        """
        Return all nodes that would be affected (directly or transitively) if
        node_id were removed from the causal system.  This is the set of all
        descendants of node_id that have node_id as their *only* causal ancestor
        for at least one of their incoming paths.

        Simplified implementation: returns all descendants.  A more precise
        version would check whether each descendant has an alternate causal
        path not going through node_id.  Callers should treat this as an
        *upper bound* on impact.
        """
        return self.descendants_of(node_id)

    def counterfactual_impact(self, cause_id: str, target_id: str) -> bool:
        """True if cause_id is on at least one causal path to target_id."""
        if cause_id == target_id:
            return True
        # cause_id must be reachable from cause_id to target_id via out-edges
        return self._is_reachable(cause_id, target_id)

    def shortest_causal_path(self, source_id: str, target_id: str) -> list[str]:
        """
        BFS shortest path from source to target following causal edges.
        Returns list of node IDs (inclusive) or empty list if no path.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return []
        if source_id == target_id:
            return [source_id]
        from collections import deque
        queue: deque[list[str]] = deque([[source_id]])
        visited: set[str] = {source_id}
        while queue:
            path = queue.popleft()
            current = path[-1]
            for edge in self._out.get(current, []):
                nxt = edge.effect_id
                if nxt == target_id:
                    return path + [nxt]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(path + [nxt])
        return []

    # ------------------------------------------------------------------
    # Risk propagation
    # ------------------------------------------------------------------

    def transitive_risk(self, node_id: str) -> float:
        """
        Max risk score of anything causally downstream of node_id (inclusive).
        Weighted by edge strength along each path.  Uses pessimistic (max) aggregation.
        """
        if node_id not in self._nodes:
            return 0.0

        # DFS with accumulated strength product.
        # risk_at_node = node.risk_prior * product_of_edge_strengths_on_path
        best: float = self._nodes[node_id].risk_prior
        stack: list[tuple[str, float]] = [(node_id, 1.0)]
        visited: set[str] = set()

        while stack:
            nid, accumulated_strength = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            node = self._nodes.get(nid)
            if node:
                effective_risk = node.risk_prior * accumulated_strength
                if effective_risk > best:
                    best = effective_risk
            for edge in self._out.get(nid, []):
                stack.append((edge.effect_id, accumulated_strength * edge.strength))

        return min(1.0, best)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._out.values())

    def get_node(self, node_id: str) -> CausalNode | None:
        return self._nodes.get(node_id)

    def all_nodes(self) -> list[CausalNode]:
        return list(self._nodes.values())

    def all_edges(self) -> list[CausalEdge]:
        return [e for edges in self._out.values() for e in edges]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to plain JSON-compatible dict (for audit logging)."""
        return {
            "nodes": [
                {"id": n.id, "label": n.label, "risk_prior": n.risk_prior}
                for n in self._nodes.values()
            ],
            "edges": [
                {"cause": e.cause_id, "effect": e.effect_id, "strength": e.strength, "description": e.description}
                for e in self.all_edges()
            ],
        }


class CyclicCausalError(ValueError):
    """Raised when adding a causal edge would create a cycle in the DAG."""


# ---------------------------------------------------------------------------
# Graph builder: infer causal structure from plan step actions
# ---------------------------------------------------------------------------

# Verb patterns that imply a causal relationship between entities in an action string.
# Format: (verb_pattern, effect_template) where %s is replaced by the extracted entity.
_CAUSAL_VERB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdelete\b|\bdrop\b|\bremove\b", re.I), "deletion"),
    (re.compile(r"\bdeploy\b|\blaunch\b|\bstart\b|\benable\b", re.I), "activation"),
    (re.compile(r"\bdisable\b|\bstop\b|\bshutdown\b|\bterminate\b", re.I), "deactivation"),
    (re.compile(r"\btransfer\b|\bmove\b|\bmigrate\b", re.I), "relocation"),
    (re.compile(r"\bupdate\b|\bmodify\b|\bchange\b|\bpatch\b", re.I), "modification"),
    (re.compile(r"\bconnect\b|\blink\b|\bintegrate\b|\bwire\b", re.I), "connection"),
    (re.compile(r"\bcreate\b|\bbuild\b|\binstall\b|\badd\b", re.I), "creation"),
    (re.compile(r"\bsend\b|\bnotify\b|\balert\b|\btrigger\b", re.I), "notification"),
]

# Words that are too generic to be useful entity names.
_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "this", "that", "it", "its", "is", "are", "was", "were",
    "to", "for", "in", "on", "at", "by", "of", "with", "and", "or", "not",
    "be", "do", "does", "did", "done", "all", "any", "some", "each",
    "step", "action", "task", "goal", "process", "system", "use", "using",
})


def _extract_entities(action: str) -> list[str]:
    """
    Heuristically extract entity-like nouns from an action string.
    Returns a deduplicated list of lowercase tokens that look like entity names.
    """
    # Strip leading verb (first word), tokenise rest.
    tokens = re.sub(r"[^a-zA-Z0-9_\-]", " ", action).lower().split()
    entities: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        if len(tok) >= 3 and tok not in _STOPWORDS and tok not in seen:
            entities.append(tok)
            seen.add(tok)
    return entities[:6]  # cap to avoid explosion


def build_graph_from_actions(
    actions: list[str],
    high_risk_node_ids: set[str] | None = None,
) -> CausalGraph:
    """
    Infer a causal graph from a sequence of plan step actions.

    Strategy:
    - Each action that modifies/creates entity E creates a node for E.
    - Sequential actions on the same entity create causal edges (later depends on earlier).
    - Actions with "high risk" verbs (delete, deploy, send) get a higher risk_prior.
    - Known high-risk node IDs (from caller, e.g. safety vault matched entities) get risk_prior=0.8.

    This is a best-effort structural inference — not semantically perfect — but deterministic
    and produces a real dependency graph the planner can traverse.
    """
    graph = CausalGraph()
    high_risk_ids = high_risk_node_ids or set()

    # Map entity -> list of (step_index, node_id) that last touched it.
    entity_last_step: dict[str, int] = {}
    # step_index -> list of node_ids created/modified at that step.
    step_nodes: list[list[str]] = []

    for idx, action in enumerate(actions):
        action_lower = action.lower()
        entities = _extract_entities(action)

        # Determine risk_prior for nodes at this step.
        is_high_risk_verb = any(pat.search(action_lower) for pat, _ in _CAUSAL_VERB_PATTERNS[:4])
        base_risk = 0.6 if is_high_risk_verb else 0.25

        current_step_nodes: list[str] = []
        for entity in entities:
            node_id = entity
            risk = 0.8 if node_id in high_risk_ids else base_risk
            graph.add_node(node_id, label=entity, risk_prior=risk)
            current_step_nodes.append(node_id)

            # Sequential dependency: if this entity was touched in a previous step,
            # add a causal edge from the previous step's primary node to this one.
            if entity in entity_last_step:
                prev_step = entity_last_step[entity]
                if step_nodes[prev_step]:
                    prev_primary = step_nodes[prev_step][0]
                    if prev_primary != node_id:
                        try:
                            graph.add_edge(
                                prev_primary,
                                node_id,
                                strength=0.7,
                                description=f"step {prev_step} -> step {idx} ({action[:80]})",
                            )
                        except CyclicCausalError:
                            pass  # skip edges that would create cycles

            entity_last_step[entity] = idx

        # Intra-step causal chain: first entity in step causes changes in later entities.
        for i in range(1, len(current_step_nodes)):
            try:
                graph.add_edge(
                    current_step_nodes[0],
                    current_step_nodes[i],
                    strength=0.5,
                    description=f"co-modified at step {idx}",
                )
            except CyclicCausalError:
                pass

        step_nodes.append(current_step_nodes)

    return graph


# ---------------------------------------------------------------------------
# Graph-aware risk summary (for causal_inference integration)
# ---------------------------------------------------------------------------

def graph_risk_summary(graph: CausalGraph, action: str) -> dict[str, Any]:
    """
    Given a causal graph and a proposed action, return a structured risk summary:
    - affected_nodes: all nodes transitively downstream of entities in the action
    - max_transitive_risk: highest risk score anywhere downstream
    - high_risk_nodes: nodes with transitive_risk >= 0.6
    - counterfactual_paths: for each high-risk node, the shortest causal path from action entity

    Returns a plain dict suitable for JSON serialisation.
    """
    entities = _extract_entities(action)
    affected: set[str] = set()
    max_risk: float = 0.0
    high_risk: list[dict[str, Any]] = []
    cf_paths: list[dict[str, Any]] = []

    for entity in entities:
        if entity not in (n.id for n in graph.all_nodes()):
            continue
        descendants = graph.descendants_of(entity)
        affected.update(descendants)
        tr = graph.transitive_risk(entity)
        if tr > max_risk:
            max_risk = tr
        for d in descendants:
            node = graph.get_node(d)
            if node and node.risk_prior >= 0.6:
                path = graph.shortest_causal_path(entity, d)
                high_risk.append({"node": d, "risk": node.risk_prior})
                cf_paths.append({"from": entity, "to": d, "path": path})

    return {
        "affected_nodes": sorted(affected),
        "max_transitive_risk": round(max_risk, 3),
        "high_risk_nodes": high_risk,
        "counterfactual_paths": cf_paths,
        "graph_node_count": graph.node_count(),
        "graph_edge_count": graph.edge_count(),
    }
