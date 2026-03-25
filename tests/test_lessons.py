"""Lesson recall tests — avoid retrieval contamination for social prompts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rain.learning.lessons import recall_lessons, store_lesson
from rain.memory.store import MemoryStore


class TestLessonRecall(unittest.TestCase):
    """Lesson retrieval must not inject unrelated context into social intros."""

    def test_creator_intro_skips_lessons(self) -> None:
        """Creator intro prompts must not retrieve lessons (avoids contamination)."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(m, "Writing all ideas to a file", "Refused", "User accepted")
            store_lesson(m, "Exploring alternatives without autonomy", "Escalated", "Blocked")
            # Creator intro should return no lessons
            lessons = recall_lessons(m, "I am the person who built you. Nice to meet you.")
            self.assertEqual(lessons, [], "Creator intro must not retrieve lessons")

    def test_social_greeting_skips_lessons(self) -> None:
        """Short social greetings must not retrieve lessons."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(m, "Hello world bug", "Fixed with print", "Resolved")
            lessons = recall_lessons(m, "Hello Rain")
            self.assertEqual(lessons, [], "Social greeting must not retrieve lessons")

    def test_substantive_query_retrieves_relevant(self) -> None:
        """Substantive queries with overlap should still retrieve lessons."""
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_lesson(m, "Database connection timeout", "Retry with backoff", "Resolved")
            lessons = recall_lessons(m, "How do I fix database connection timeout errors?")
            self.assertGreater(len(lessons), 0, "Relevant lesson should be retrieved")
            self.assertIn("database", str(lessons[0]).lower())
