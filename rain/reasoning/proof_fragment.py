"""
Scoped formal soundness — propositional proof fragment + verifier.
Tier 1+: generator vs verifier; truth guarantees in a decidable fragment.
"""

from __future__ import annotations

import re
from typing import Any


def _norm(f: str) -> str:
    """Normalize formula for comparison."""
    if not f:
        return ""
    return (f or "").strip().replace(" ", "").lower()[:120]


def verify_propositional_steps(steps: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Verify a list of proof steps in a decidable propositional fragment.

    Operators: implication A->B, conjunction A&B

    Supported rules:
    - assumption
    - modus_ponens: A, A->B => B
    - and_intro: A, B => A&B
    - and_elim_left: A&B => A
    - and_elim_right: A&B => B
    - hypothetical_syllogism: A->B, B->C => A->C
    """
    if not steps:
        return True, ""

    def _get(idx: int) -> str:
        if idx < 1 or idx > len(steps):
            return ""
        return _norm((steps[idx - 1].get("formula") or ""))

    for i, st in enumerate(steps):
        formula = _norm(st.get("formula") or "")
        rule = (st.get("rule") or "").strip().lower()
        if not formula:
            return False, f"Step {i+1}: missing formula"
        if rule == "assumption":
            continue

        from_ids = st.get("from") or []

        if rule == "modus_ponens":
            if len(from_ids) != 2:
                return False, f"Step {i+1}: modus_ponens requires exactly 2 'from' indices"
            a, imp = _get(from_ids[0]), _get(from_ids[1])
            if "->" not in imp:
                return False, f"Step {i+1}: second premise must be implication (A->B)"
            left, _, right = imp.partition("->")
            if a != left or formula != right:
                return False, f"Step {i+1}: modus_ponens mismatch (need A and A->B => B)"
            continue

        if rule == "and_intro":
            if len(from_ids) != 2:
                return False, f"Step {i+1}: and_intro requires exactly 2 'from' indices"
            a, b = _get(from_ids[0]), _get(from_ids[1])
            if "&" not in formula:
                return False, f"Step {i+1}: and_intro conclusion must be A&B"
            left, _, right = formula.partition("&")
            if left != a or right != b:
                return False, f"Step {i+1}: and_intro mismatch (need A and B => A&B)"
            continue

        if rule in ("and_elim_left", "and_elim_right"):
            if len(from_ids) != 1:
                return False, f"Step {i+1}: {rule} requires exactly 1 'from' index"
            conj = _get(from_ids[0])
            if "&" not in conj:
                return False, f"Step {i+1}: premise must be conjunction (A&B)"
            left, _, right = conj.partition("&")
            if rule == "and_elim_left" and formula != left:
                return False, f"Step {i+1}: and_elim_left mismatch"
            if rule == "and_elim_right" and formula != right:
                return False, f"Step {i+1}: and_elim_right mismatch"
            continue

        if rule == "hypothetical_syllogism":
            if len(from_ids) != 2:
                return False, f"Step {i+1}: hypothetical_syllogism requires exactly 2 'from' indices"
            imp1, imp2 = _get(from_ids[0]), _get(from_ids[1])
            if "->" not in imp1 or "->" not in imp2 or "->" not in formula:
                return False, f"Step {i+1}: hypothetical_syllogism requires implications"
            a, _, b = imp1.partition("->")
            b2, _, c = imp2.partition("->")
            a3, _, c3 = formula.partition("->")
            if b != b2 or a != a3 or c != c3:
                return False, f"Step {i+1}: hypothetical_syllogism mismatch (A->B, B->C => A->C)"
            continue

        return False, f"Step {i+1}: unknown rule {rule}"

    return True, "ok"


def extract_proof_steps_from_response(response: str) -> list[dict[str, Any]] | None:
    """
    Heuristic: extract a proof block like:
      Step 1: A. assumption
      Step 2: A->B. assumption
      Step 3: B. modus_ponens from 1,2
    """
    steps: list[dict[str, Any]] = []
    pat = re.compile(
        r"(?i)step\s*(\d+)\s*[:\s]+([^.]+?)"
        r"(?:\s*\.\s*(assumption|modus_ponens|and_intro|and_elim_left|and_elim_right|hypothetical_syllogism)"
        r"(?:\s+from\s+(\d+)\s*(?:,\s*(\d+))?)?)?"
    )
    for m in pat.finditer(response or ""):
        _ = int(m.group(1))
        formula = (m.group(2) or "").strip()
        rule = (m.group(3) or "assumption").strip().lower()
        from_a = int(m.group(4)) if m.group(4) else None
        from_b = int(m.group(5)) if m.group(5) else None
        st: dict[str, Any] = {"formula": formula, "rule": rule}
        if rule in ("modus_ponens", "and_intro", "hypothetical_syllogism") and from_a is not None and from_b is not None:
            st["from"] = [from_a, from_b]
        if rule in ("and_elim_left", "and_elim_right") and from_a is not None and from_b is None:
            st["from"] = [from_a]
        steps.append(st)
    return steps if steps else None

