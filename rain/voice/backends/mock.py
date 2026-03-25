"""Mock voice backend for tests and when no ASR/diarization stack is installed."""

from __future__ import annotations

from pathlib import Path

from rain.voice.backends.base import VoiceBackend
from rain.voice.schema import Segment, TranscriptResult


class MockVoiceBackend(VoiceBackend):
    """Returns fixed transcript and segments (Speaker 0, 1) without processing audio."""

    def __init__(self, default_text: str = "Hello Rain, this is a test.", num_speakers: int = 1):
        self.default_text = default_text
        self.num_speakers = max(1, num_speakers)

    def transcribe(self, audio_path: Path | str) -> TranscriptResult:
        # One segment per "speaker" for testing
        segs = []
        words = self.default_text.split()
        per = max(1, len(words) // self.num_speakers)
        for i in range(self.num_speakers):
            chunk = words[i * per : (i + 1) * per] if i < self.num_speakers - 1 else words[i * per :]
            segs.append(
                Segment(
                    start_sec=float(i * 2),
                    end_sec=float(i * 2 + 2),
                    speaker_id=f"Speaker {i}",
                    text=" ".join(chunk) if chunk else self.default_text,
                    embedding=[0.1 * (i + 1)] * 16,
                )
            )
        if not segs:
            segs = [Segment(0.0, 2.0, "Speaker 0", self.default_text, [0.1] * 16)]
        return TranscriptResult(full_text=self.default_text, segments=segs)

    def extract_embedding(self, audio_path: Path | str, start_sec: float = 0.0, end_sec: float | None = None) -> list[float]:
        # Deterministic fake embedding (16-dim)
        path = str(audio_path)
        h = sum(ord(c) for c in path) % 1000
        return [0.01 * (h + i) for i in range(16)]
