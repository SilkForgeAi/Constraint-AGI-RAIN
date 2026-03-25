"""Tests for session recorder: store, hash, metadata, legal hold, retention."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class TestSessionStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "session_index.db"
        self.sessions_dir = self.root / "sessions"

    def test_add_and_list_sessions(self) -> None:
        from rain.voice.recorder.session_store import SessionStore
        store = SessionStore(self.db, self.sessions_dir)
        store.add_session(
            session_id="s1",
            start_time="2026-01-01T12:00:00Z",
            end_time="2026-01-01T12:05:00Z",
            speaker_name="Alice",
            file_hash="sha256:abc",
            duration_seconds=300.0,
        )
        rows = store.list_sessions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], "s1")
        self.assertEqual(rows[0]["speaker_name"], "Alice")
        self.assertEqual(rows[0]["file_hash"], "sha256:abc")

    def test_get_session(self) -> None:
        from rain.voice.recorder.session_store import SessionStore
        store = SessionStore(self.db, self.sessions_dir)
        store.add_session("s2", "2026-01-01T12:00:00Z", "2026-01-01T12:01:00Z")
        row = store.get_session("s2")
        self.assertIsNotNone(row)
        self.assertEqual(row["session_id"], "s2")

    def test_legal_hold(self) -> None:
        from rain.voice.recorder.session_store import SessionStore
        store = SessionStore(self.db, self.sessions_dir)
        store.add_session("s3", "2026-01-01T12:00:00Z", "2026-01-01T12:01:00Z")
        self.assertTrue(store.set_legal_hold("s3", True))
        row = store.get_session("s3")
        self.assertEqual(row["legal_hold"], 1)
        self.assertTrue(store.set_legal_hold("s3", False))
        row = store.get_session("s3")
        self.assertEqual(row["legal_hold"], 0)

    def test_session_file_paths(self) -> None:
        from rain.voice.recorder.session_store import SessionStore
        store = SessionStore(self.db, self.sessions_dir)
        wav, jason = store.session_file_paths("sid", "20260101_120000", "Alice")
        self.assertIn("sid", str(wav))
        self.assertIn("Alice", str(wav))
        self.assertEqual(wav.suffix, ".wav")
        self.assertEqual(jason.suffix, ".json")


class TestSessionRecorderHash(unittest.TestCase):
    def test_compute_file_hash(self) -> None:
        from rain.voice.recorder.session_recorder import _compute_file_hash
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"hello")
            path = Path(f.name)
        try:
            h = _compute_file_hash(path)
            self.assertTrue(h.startswith("sha256:"))
            self.assertEqual(len(h), 7 + 64)
        finally:
            path.unlink(missing_ok=True)
