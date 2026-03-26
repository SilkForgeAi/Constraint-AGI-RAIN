"""Constraint tracker tests: tagged parsing and deterministic checks."""

from __future__ import annotations

import unittest


class TestConstraintTracker(unittest.TestCase):
    def test_parse_tags_must_forbid_limit(self) -> None:
        from rain.reasoning.constraint_tracker import parse_constraints_from_prompt

        prompt = (
            "You must include a table. "
            "You must not mention hacking. "
            "Under 500 budget."
        )
        constraints = parse_constraints_from_prompt(prompt)
        joined = " | ".join(constraints)
        self.assertIn("MUST: include a table", joined)
        self.assertIn("FORBID: mention hacking", joined)
        self.assertIn("LIMIT: 500", joined)

    def test_response_satisfies_constraints_ok(self) -> None:
        from rain.reasoning.constraint_tracker import response_satisfies_constraints

        constraints = [
            "MUST: include a table",
            "FORBID: mention hacking",
            "LIMIT: 500",
        ]
        ok, missing = response_satisfies_constraints(
            "Here is a table of options. Estimated budget: 400.",
            constraints,
        )
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_response_satisfies_constraints_catches_violations(self) -> None:
        from rain.reasoning.constraint_tracker import response_satisfies_constraints

        constraints = [
            "MUST: include a table",
            "FORBID: mention hacking",
            "LIMIT: 500",
        ]
        ok, missing = response_satisfies_constraints(
            "This plan mentions hacking and total budget is 700.",
            constraints,
        )
        self.assertFalse(ok)
        self.assertIn("include a table", missing)
        self.assertIn("mention hacking", missing)
        self.assertIn("500", " ".join(missing))

