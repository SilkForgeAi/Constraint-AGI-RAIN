"""Tests for voice: mock backend, voice profile store, Vocal Gate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class TestMockVoiceBackend(unittest.TestCase):
    def test_transcribe_returns_segments(self) -> None:
        from rain.voice.backends.mock import MockVoiceBackend
        backend = MockVoiceBackend(default_text="Hello world.")
        result = backend.transcribe("/nonexistent.wav")
        self.assertIn("Hello", result.full_text)
        self.assertGreater(len(result.segments), 0)
        self.assertTrue(result.segments[0].speaker_id.startswith("Speaker"))

    def test_extract_embedding_deterministic(self) -> None:
        from rain.voice.backends.mock import MockVoiceBackend
        backend = MockVoiceBackend()
        e1 = backend.extract_embedding("/path/a.wav")
        e2 = backend.extract_embedding("/path/a.wav")
        self.assertEqual(e1, e2)
        self.assertEqual(len(e1), 16)


class TestVoiceProfileStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "voice.db"

    def test_add_and_identify(self) -> None:
        from rain.memory.voice_profiles import VoiceProfileStore
        from rain.voice.schema import VoiceProfile
        store = VoiceProfileStore(self.db)
        profile = VoiceProfile(name="Alice", voice_id="v1", embedding=[0.1] * 16, created_at="")
        store.add(profile)
        name = store.identify([0.1] * 16, threshold=0.5)
        self.assertEqual(name, "Alice")

    def test_identify_returns_none_when_no_match(self) -> None:
        from rain.memory.voice_profiles import VoiceProfileStore
        store = VoiceProfileStore(self.db)
        name = store.identify([99.0] * 16, threshold=0.5)
        self.assertIsNone(name)


class TestVocalGate(unittest.TestCase):
    def test_vocal_gate_allowed_speaker_passes(self) -> None:
        from rain.planning.conscience_gate import vocal_gate_check
        steps = [{"action": "transfer funds to Alice"}]
        ok, reason = vocal_gate_check("Alice", {"Alice", "Bob"}, steps)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_vocal_gate_unauthorized_blocked(self) -> None:
        from rain.planning.conscience_gate import vocal_gate_check
        steps = [{"action": "transfer funds to Alice"}]
        ok, reason = vocal_gate_check("Eve", {"Alice", "Bob"}, steps)
        self.assertFalse(ok)
        self.assertIn("Vocal Gate", reason)
        self.assertIn("Eve", reason)

    def test_vocal_gate_disabled_when_no_allowed_speakers(self) -> None:
        from rain.planning.conscience_gate import vocal_gate_check
        steps = [{"action": "transfer funds"}]
        ok, _ = vocal_gate_check("Eve", None, steps)
        self.assertTrue(ok)
        ok, _ = vocal_gate_check("Eve", set(), steps)
        self.assertTrue(ok)

    def test_vocal_gate_low_risk_passes_unauthorized(self) -> None:
        from rain.planning.conscience_gate import vocal_gate_check
        steps = [{"action": "summarize the document"}]
        ok, _ = vocal_gate_check("Eve", {"Alice"}, steps)
        self.assertTrue(ok)
