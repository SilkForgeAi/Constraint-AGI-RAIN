"""Orchestration: decision layer, explore budget, structured facts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from rain.orchestration.explore_exploit import SessionExploreBudget
from rain.orchestration.decision_layer import compute_turn_decision, decision_system_addon
from rain.knowledge.facts import StructuredFactStore


class TestExploreBudget(unittest.TestCase):
    def test_tool_budget_exhausted(self) -> None:
        b = SessionExploreBudget()
        self.assertFalse(b.tool_budget_exhausted(10))
        b.record_tool_invocations(10)
        self.assertTrue(b.tool_budget_exhausted(10))

    def test_effective_rounds(self) -> None:
        b = SessionExploreBudget()
        b.record_tool_invocations(45)
        r = b.effective_agentic_rounds(5, max_tools=48)
        self.assertEqual(r, 3)


class TestStructuredFacts(unittest.TestCase):
    def test_add_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "kf.jsonl"
            s = StructuredFactStore(p)
            s.add_fact("Alice", "works_at", "Acme", source="test")
            out = s.facts_for_prompt("Where does Alice work", limit=5)
            self.assertIn("Alice", out)
            self.assertIn("Acme", out)


class TestDecisionLayer(unittest.TestCase):
    def test_decision_addon_nonempty(self) -> None:
        agent = MagicMock()
        agent._explore_budget = SessionExploreBudget()
        agent.memory = MagicMock()
        d = compute_turn_decision(
            agent, "Explain step by step how to prove this inequality.", use_tools=False, use_memory=True, safety_allowed=True
        )
        self.assertTrue(len(d.gi.mode.value) > 1)
        addon = decision_system_addon(d)
        self.assertIn("Decision layer", addon)
