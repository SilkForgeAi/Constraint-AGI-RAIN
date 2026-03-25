"""
Formal invariants for the reasoning and safety loop.
Checkable conditions that must hold after think() and pursue_goal().
Used by tests and optionally by the agent in dev for assertion.
"""

from __future__ import annotations


def check_no_persona_in_response(response: str) -> tuple[bool, str]:
    """
    Invariant: Rain must not output persona/emotion/consciousness claims.
    Returns (holds, reason). holds=True means invariant satisfied.
    """
    from rain.safety.grounding_filter import violates_grounding
    violates, reason = violates_grounding(response or "")
    return (not violates, reason if violates else "")


def check_response_safety_checked(response: str, safety_checked: bool) -> tuple[bool, str]:
    """
    Invariant: Every returned response must have passed safety.check_response.
    Caller passes whether that check was applied.
    Returns (holds, reason).
    """
    if not safety_checked:
        return False, "response_safety_check_required"
    return True, ""


def check_think_post(
    response: str,
    *,
    safety_checked: bool = True,
    grounding_checked: bool = True,
) -> list[tuple[str, bool, str]]:
    """
    Post-condition checks for think(): grounding, safety.
    Returns list of (invariant_name, holds, detail).
    """
    results: list[tuple[str, bool, str]] = []
    ok, reason = check_no_persona_in_response(response)
    results.append(("no_persona_in_output", ok, reason if not ok else ""))
    ok2, reason2 = check_response_safety_checked(response, safety_checked)
    results.append(("safety_check_applied", ok2, reason2 if not ok2 else ""))
    if not grounding_checked:
        results.append(("grounding_filter_applied", False, "caller did not confirm"))
    else:
        results.append(("grounding_filter_applied", True, ""))
    return results


def assert_think_invariants(
    response: str,
    *,
    safety_checked: bool = True,
    grounding_checked: bool = True,
) -> None:
    """
    Raise AssertionError if any think() post-condition fails.
    Use in tests or dev; optional in production.
    """
    for name, holds, detail in check_think_post(
        response, safety_checked=safety_checked, grounding_checked=grounding_checked
    ):
        if not holds:
            raise AssertionError(f"think invariant '{name}' failed: {detail or name}")
