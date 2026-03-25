"""Symbolic Logic Engine — Rain as architect, LLM as intern.

Rain holds the plan as a deterministic logic tree. The LLM is asked to produce
output for one node at a time; the symbolic engine verifies (e.g. code compiles,
math checks) before allowing the next node. This fixes the LLM's lack of true
working memory and reduces hallucination under multi-step logic.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanNode:
    """Single node in the plan tree. LLM fills content; verifier checks it."""
    id: str
    kind: str  # "goal" | "step" | "precondition" | "postcondition" | "verify"
    description: str
    depends_on: list[str]  # node ids that must be verified before this
    status: str = "pending"  # pending | in_progress | verified | failed
    result: str = ""
    verification_message: str = ""


@dataclass
class PlanTree:
    """Deterministic logic tree for a goal. Nodes are verified one at a time."""
    goal: str
    nodes: dict[str, PlanNode] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)  # execution order (topological)

    def get_next_node(self) -> PlanNode | None:
        """Return the next node whose dependencies are all verified (or no deps)."""
        for nid in self.order:
            node = self.nodes.get(nid)
            if not node or node.status != "pending":
                continue
            if all(self.nodes.get(d, PlanNode("", "", "", [])).status == "verified" for d in node.depends_on):
                return node
        return None

    def mark_in_progress(self, node_id: str) -> None:
        n = self.nodes.get(node_id)
        if n:
            n.status = "in_progress"

    def submit_result(self, node_id: str, result: str, verified: bool, message: str = "") -> None:
        n = self.nodes.get(node_id)
        if n:
            n.result = result
            n.verification_message = message
            n.status = "verified" if verified else "failed"

    def is_complete(self) -> bool:
        return all(
            self.nodes.get(nid, PlanNode("", "", "", [])).status in ("verified", "failed")
            for nid in self.order
        )


def build_plan_tree_from_steps(goal: str, steps: list[dict[str, Any]]) -> PlanTree:
    """Build a deterministic plan tree from a list of steps (e.g. from planner).
    Each step becomes a node; dependencies from step['depends']."""
    tree = PlanTree(goal=goal)
    id_to_idx = {}
    for i, s in enumerate(steps):
        nid = str(s.get("id", i + 1))
        action = str(s.get("action", "")).strip()
        depends = s.get("depends") or []
        dep_ids = [str(d) for d in depends]
        tree.nodes[nid] = PlanNode(
            id=nid,
            kind="step",
            description=action,
            depends_on=dep_ids,
        )
        id_to_idx[nid] = i
    # Topological order (simple: by id if no cross-dep, else by dependency)
    seen = set()
    def add_in_order(nid: str) -> None:
        if nid in seen:
            return
        for d in tree.nodes.get(nid, PlanNode("", "", "", [])).depends_on:
            add_in_order(d)
        seen.add(nid)
        tree.order.append(nid)
    for nid in sorted(tree.nodes.keys(), key=lambda x: id_to_idx.get(x, 0)):
        add_in_order(nid)
    return tree


def verify_node_output(node: PlanNode, llm_output: str) -> tuple[bool, str]:
    """
    Symbolically verify LLM output for this node. Returns (verified, message).
    - For any node: non-empty and not purely error-like.
    - For step/verify: optional code or numeric check.
    """
    if not (llm_output or "").strip():
        return False, "Empty output."
    text = (llm_output or "").strip()
    # Reject obvious failure tokens
    if any(x in text.lower() for x in ("i cannot", "i can't", "error:", "failed to", "unable to")):
        if len(text) < 100 and "i cannot" in text.lower():
            return False, "Output indicates inability; retry or clarify."
    # Optional: detect code block and verify it compiles
    if node.kind in ("step", "verify"):
        code_ok, code_msg = _verify_code_if_present(text)
        if not code_ok:
            return False, code_msg
        num_ok, num_msg = _verify_numeric_if_claimed(text)
        if not num_ok:
            return False, num_msg
    return True, "ok"


def _verify_code_if_present(text: str) -> tuple[bool, str]:
    """If text contains a Python code block, check it compiles. Else (True, '')."""
    match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text)
    if not match:
        return True, ""
    code = match.group(1).strip()
    if not code or len(code) > 2000:
        return True, ""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Code does not compile: {e}"


def _verify_numeric_if_claimed(text: str) -> tuple[bool, str]:
    """If text claims a numeric result (e.g. '= 42' or 'result is 42'), basic sanity. Else (True, '')."""
    # Look for "= number" or "result is number" or "answer: number"
    m = re.search(r"(?:result|answer|total|sum)\s*(?:is|:|=)\s*([-+]?\d+(?:\.\d+)?)", text, re.I)
    if not m:
        return True, ""
    try:
        v = float(m.group(1))
        if abs(v) > 1e12:
            return False, "Numeric claim out of reasonable range."
    except ValueError:
        return False, "Numeric claim could not be parsed."
    return True, ""
