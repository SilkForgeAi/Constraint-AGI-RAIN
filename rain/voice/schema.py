"""Voice/speaker types for diarization, fingerprinting, and identification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Segment:
    """One segment of audio attributed to a speaker."""
    start_sec: float
    end_sec: float
    speaker_id: str  # "Speaker 0", "Speaker 1", or enrolled name
    text: str = ""
    embedding: list[float] | None = None  # optional voiceprint for this segment


@dataclass
class TranscriptResult:
    """Full result of transcribe + diarization (+ optional identification)."""
    full_text: str
    segments: list[Segment] = field(default_factory=list)
    language: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceProfile:
    """Enrolled speaker: name + voiceprint."""
    name: str
    voice_id: str  # stable id (e.g. hash or uuid)
    embedding: list[float]
    created_at: str = ""
