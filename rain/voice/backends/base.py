"""Abstract voice backend: transcribe, diarize, and optional voiceprint."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rain.voice.schema import Segment, TranscriptResult, VoiceProfile


class VoiceBackend(ABC):
    """Backend for ASR, diarization, and speaker identification."""

    @abstractmethod
    def transcribe(self, audio_path: Path | str) -> TranscriptResult:
        """Transcribe audio and return segments with speaker labels (Speaker 0, 1, ...)."""
        ...

    @abstractmethod
    def extract_embedding(self, audio_path: Path | str, start_sec: float = 0.0, end_sec: float | None = None) -> list[float]:
        """Extract a single voice embedding from audio (or segment). Returns fixed-size vector."""
        ...

    def enroll(self, name: str, audio_path: Path | str, voice_id: str | None = None) -> VoiceProfile:
        """Create a voice profile from a reference clip (e.g. 10–20 s)."""
        emb = self.extract_embedding(audio_path)
        import hashlib
        vid = voice_id or hashlib.sha256(f"{name}:{len(emb)}".encode()).hexdigest()[:16]
        from datetime import datetime, timezone
        return VoiceProfile(name=name, voice_id=vid, embedding=emb, created_at=datetime.now(timezone.utc).isoformat())

    def identify(self, embedding: list[float], profiles: list[VoiceProfile], threshold: float = 0.5) -> str | None:
        """Match embedding to nearest profile. Returns name if distance below threshold else None."""
        if not profiles or not embedding:
            return None
        best_name: str | None = None
        best_dist = float("inf")
        for p in profiles:
            d = _l2(embedding, p.embedding)
            if d < best_dist and d <= threshold:
                best_dist = d
                best_name = p.name
        return best_name


def _l2(a: list[float], b: list[float]) -> float:
    """L2 distance between two vectors."""
    if len(a) != len(b):
        return float("inf")
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
