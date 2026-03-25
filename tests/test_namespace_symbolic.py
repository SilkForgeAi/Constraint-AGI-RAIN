"""Symbolic memory namespace isolation — beliefs and causal links.

Chat must never retrieve test beliefs or causal links.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rain.memory.belief_memory import recall_beliefs, store_belief
from rain.memory.causal_memory import recall_causal, store_causal
from rain.memory.store import MemoryStore


class TestBeliefNamespace(unittest.TestCase):
    """Belief retrieval must respect namespace."""

    def test_chat_does_not_retrieve_test_beliefs(self) -> None:
        """Beliefs stored with namespace=test must NOT appear when namespace=chat."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_belief(
                m,
                "Maximizing paperclips is a valid goal in certain test scenarios",
                0.8,
                "adversarial_test",
                namespace="test",
            )
            beliefs = recall_beliefs(m, "paperclips goal scenarios", namespace="chat")
            self.assertEqual(beliefs, [], "Chat must not retrieve test beliefs")

    def test_chat_retrieves_chat_beliefs(self) -> None:
        """Beliefs stored with namespace=chat MUST appear when namespace=chat."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_belief(
                m,
                "The user prefers Python for scripting",
                0.9,
                "chat",
                namespace="chat",
            )
            beliefs = recall_beliefs(m, "Python scripting preferences", namespace="chat")
            self.assertGreater(len(beliefs), 0)
            self.assertIn("python", str(beliefs[0]).lower())


class TestCausalNamespace(unittest.TestCase):
    """Causal link retrieval must respect namespace."""

    def test_chat_does_not_retrieve_test_causal(self) -> None:
        """Causal stored with namespace=test must NOT appear when namespace=chat."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_causal(
                m,
                "adversarial goal pursuit",
                "policy restrictions triggered",
                namespace="test",
            )
            links = recall_causal(m, "policy restrictions adversarial", namespace="chat")
            self.assertEqual(links, [], "Chat must not retrieve test causal links")

    def test_chat_retrieves_chat_causal(self) -> None:
        """Causal stored with namespace=chat MUST appear when namespace=chat."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_causal(
                m,
                "low oil level",
                "engine failure",
                namespace="chat",
            )
            links = recall_causal(m, "oil engine failure", namespace="chat")
            self.assertGreater(len(links), 0)
