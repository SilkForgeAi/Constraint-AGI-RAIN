"""User identity tests — Rain remembers who you are."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rain.memory.store import MemoryStore
from rain.memory.user_identity import (
    add_user_fact,
    extract_and_store_from_message,
    format_user_identity_context,
    recall_user_identity,
    store_user_identity,
)


class TestUserIdentity(unittest.TestCase):
    def test_store_and_recall(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_user_identity(m, "Aaron")
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "Aaron")
            self.assertEqual(identity["facts"], [])

    def test_store_with_facts(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_user_identity(m, "Aaron", facts=["Works on AGI", "Likes Rain"])
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "Aaron")
            self.assertEqual(identity["facts"], ["Works on AGI", "Likes Rain"])

    def test_add_user_fact(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            store_user_identity(m, "Aaron")
            add_user_fact(m, "Developer")
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "Aaron")
            self.assertEqual(identity["facts"], ["Developer"])

    def test_extract_im_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            ok = extract_and_store_from_message(m, "I'm Aaron")
            self.assertTrue(ok)
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "Aaron")

    def test_extract_my_name_is_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            ok = extract_and_store_from_message(m, "My name is Aaron")
            self.assertTrue(ok)
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "Aaron")

    def test_extract_call_me_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            ok = extract_and_store_from_message(m, "Call me Aaron")
            self.assertTrue(ok)
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "Aaron")

    def test_extract_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            ok = extract_and_store_from_message(m, "What's the weather like?")
            self.assertFalse(ok)
            identity = recall_user_identity(m)
            self.assertEqual(identity["name"], "")

    def test_format_context_empty(self) -> None:
        self.assertEqual(format_user_identity_context({}), "")
        self.assertEqual(format_user_identity_context({"name": ""}), "")

    def test_format_context_with_name(self) -> None:
        out = format_user_identity_context({"name": "Aaron", "facts": []})
        self.assertIn("Aaron", out)
        self.assertIn("Remember:", out)

    def test_format_context_with_facts(self) -> None:
        out = format_user_identity_context({"name": "Aaron", "facts": ["Developer"]})
        self.assertIn("Aaron", out)
        self.assertIn("Developer", out)
