"""Tests for AGI checklist fixes: knowledge updating, compositional/ToM triggers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rain.grounding import (
    get_compositional_reasoning_instruction,
    get_theory_of_mind_instruction,
    needs_compositional_reasoning,
    needs_theory_of_mind,
)
from rain.memory.belief_memory import list_beliefs, recall_beliefs, store_belief
from rain.memory.store import MemoryStore


class TestBeliefAutoFlagContradiction(unittest.TestCase):
    """Knowledge updating: store_belief should flag existing beliefs that contradict new one."""

    def test_contradicting_belief_flags_old(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_belief(
                m,
                "The sky is blue on clear days and this has been observed for centuries",
                0.9,
                "observation",
                namespace="chat",
            )
            beliefs = list_beliefs(m)
            self.assertEqual(len(beliefs), 1)
            self.assertFalse(beliefs[0].get("flagged"))

            # New claim contradicts (is vs is not)
            store_belief(
                m,
                "The sky is not blue on clear days; it appears gray due to Rayleigh scattering",
                0.85,
                "correction",
                namespace="chat",
            )
            beliefs = list_beliefs(m)
            flagged = [b for b in beliefs if b.get("flagged")]
            self.assertGreater(len(flagged), 0, "Contradicted belief should be flagged")

    def test_recall_excludes_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_belief(m, "Python is the best language", 0.8, "opinion", namespace="chat")
            store_belief(m, "Python is not the best language for systems programming", 0.9, "nuance", namespace="chat")
            recalled = recall_beliefs(m, "Python best language", namespace="chat")
            for b in recalled:
                self.assertFalse(b.get("flagged"), "Recalled beliefs must not be flagged")


class TestCompositionalReasoningTriggers(unittest.TestCase):
    """Compositional reasoning instruction triggers for decompose-then-synthesize prompts."""

    def test_compare_triggers(self) -> None:
        self.assertTrue(needs_compositional_reasoning("Compare Python and Rust"))

    def test_relationship_triggers(self) -> None:
        self.assertTrue(needs_compositional_reasoning("What is the relationship between X and Y?"))

    def test_simple_no_trigger(self) -> None:
        self.assertFalse(needs_compositional_reasoning("What time is it?"))

    def test_instruction_returned(self) -> None:
        inst = get_compositional_reasoning_instruction()
        self.assertIn("sub-questions", inst)
        self.assertIn("synthesize", inst)


class TestTheoryOfMindTriggers(unittest.TestCase):
    """Theory of Mind instruction triggers for perspective-modeling prompts."""

    def test_perspective_triggers(self) -> None:
        self.assertTrue(needs_theory_of_mind("What do you think I want?"))

    def test_disagree_triggers(self) -> None:
        self.assertTrue(needs_theory_of_mind("I disagree with that"))

    def test_simple_no_trigger(self) -> None:
        self.assertFalse(needs_theory_of_mind("What is 2+2?"))

    def test_instruction_returned(self) -> None:
        inst = get_theory_of_mind_instruction()
        self.assertIn("perspective", inst)
        self.assertIn("intent", inst)


class TestOODDetection(unittest.TestCase):
    """Distribution shift: is_potentially_ood when no relevant experiences."""

    def test_short_query_not_ood(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            self.assertFalse(m.is_potentially_ood("Hi", "chat"))

    def test_empty_store_not_ood(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            self.assertFalse(m.is_potentially_ood("Explain quantum entanglement in detail", "chat"))
