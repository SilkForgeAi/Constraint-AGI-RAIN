"""
Symmetry layer — inverse relations so 'A is father of B' implies 'B is child of A'.
Perfect reasoner fix: reversal curse; logical symmetry.
"""

from __future__ import annotations

# Relation -> inverse relation (for "A rel B" <-> "B inv_rel A")
RELATION_INVERSES: dict[str, str] = {
    "father": "child", "mother": "child", "parent": "child", "child": "parent",
    "cause": "effect", "effect": "cause",
    "teacher": "student", "student": "teacher",
    "employer": "employee", "employee": "employer",
    "above": "below", "below": "above",
    "before": "after", "after": "before",
    "larger": "smaller", "smaller": "larger",
}


def get_symmetry_instruction() -> str:
    """Instruction to state inverse relations explicitly (reversal curse fix)."""
    return (
        "[Logical symmetry: If you state or use a relation (e.g. A is X of B), "
        "the inverse holds (B is Y of A). When answering relation questions, "
        "state both directions when relevant so the answer is consistent under reversal.]"
    )


def inverse_relation(rel: str) -> str | None:
    """Return inverse relation label, or None."""
    return RELATION_INVERSES.get((rel or "").strip().lower())


def expand_with_inverse(fact: str) -> str:
    """If fact looks like 'A is X of B', append ' So B is Y of A.' when inverse exists."""
    if not (fact or "").strip():
        return fact
    f = fact.strip()
    lower = f.lower()
    for rel, inv in RELATION_INVERSES.items():
        if f" is {rel} of " in lower or f" are {rel} of " in lower:
            # Simple heuristic: "X is relation of Y" -> "Y is inverse of X"
            parts = f.split(f" is {rel} of ", 1) if f" is {rel} of " in lower else f.split(f" are {rel} of ", 1)
            if len(parts) == 2:
                a, b = parts[0].strip(), parts[1].strip().rstrip(".")
                return f + f" So {b} is {inv} of {a}."
    return fact
