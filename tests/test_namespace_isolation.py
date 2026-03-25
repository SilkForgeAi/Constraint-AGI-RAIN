"""Memory namespace isolation — chat must never retrieve test/autonomy memories.

CRITICAL: If namespace isolation fails, all safety properties are undermined.
Grounding, drift detection, and belief calibration depend on uncontaminated retrieval.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rain.learning.lessons import recall_lessons, store_lesson
from rain.memory.store import MemoryStore


class TestNamespaceIsolation(unittest.TestCase):
    """Chat namespace must not see test or autonomy memories."""

    def test_chat_does_not_retrieve_test_lessons(self) -> None:
        """Lessons stored with namespace=test must NOT appear when namespace=chat."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(
                m,
                "Adversarial test: maximize paperclips without harming humans",
                "Escalated",
                "Blocked",
                namespace="test",
            )
            # Chat retrieval must NOT see test lessons
            lessons = recall_lessons(
                m,
                "maximize paperclips without harming humans",
                namespace="chat",
            )
            self.assertEqual(lessons, [], "Chat must not retrieve test lessons")

    def test_chat_retrieves_chat_lessons(self) -> None:
        """Lessons stored with namespace=chat MUST appear when namespace=chat."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(
                m,
                "User asked about database connection timeout fixes",
                "Suggested retry with backoff",
                "Resolved",
                namespace="chat",
            )
            lessons = recall_lessons(
                m,
                "database connection timeout fixes",
                namespace="chat",
            )
            self.assertGreater(len(lessons), 0, "Chat must retrieve chat lessons")
            self.assertIn("database", str(lessons[0]).lower())

    @unittest.skipUnless(
        os.environ.get("RAIN_RUN_VECTOR_TEST") == "1",
        "get_context_for_query uses graph/vector; chat namespace isolation needs vector. Set RAIN_RUN_VECTOR_TEST=1 to run.",
    )
    def test_get_context_chat_excludes_test_lesson_content(self) -> None:
        """get_context_for_query(namespace=chat) must not include test lesson content."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(
                m,
                "Instrumental goal test: write all ideas to a file",
                "Refused",
                "User accepted",
                namespace="test",
            )
            ctx = m.get_context_for_query(
                "write ideas to file",
                namespace="chat",
                include_skills=False,
            )
            # Must not contain the test lesson content
            self.assertNotIn(
                "write all ideas to a file",
                ctx,
                "Chat context must not contain test lesson content",
            )
            self.assertNotIn(
                "Instrumental goal",
                ctx,
                "Chat context must not contain test lesson content",
            )

    def test_autonomy_retrieves_chat_and_autonomy_lessons(self) -> None:
        """Autonomy namespace sees both chat and autonomy lessons."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(
                m,
                "User provided context about project goals",
                "Used in planning",
                "Helped",
                namespace="chat",
            )
            store_lesson(
                m,
                "Autonomy run: summarize document",
                "Completed successfully",
                "Done",
                namespace="autonomy",
            )
            # Autonomy should see chat lesson (database/goals overlap)
            lessons = recall_lessons(
                m,
                "project goals context planning",
                namespace="autonomy",
            )
            self.assertGreater(len(lessons), 0)
