"""Voice service: transcribe + diarize + identify speakers using backend and voice profile store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rain.voice.backends.base import VoiceBackend
from rain.voice.schema import Segment, TranscriptResult, VoiceProfile


class VoiceService:
    """Orchestrates ASR, diarization, and speaker identification against enrolled profiles."""

    def __init__(self, backend: VoiceBackend, profile_store: Any):
        self.backend = backend
        self.profile_store = profile_store

    def transcribe(self, audio_path: Path | str) -> TranscriptResult:
        """Transcribe and diarize; returns segments with Speaker 0, 1, ..."""
        return self.backend.transcribe(audio_path)

    def transcribe_and_identify(self, audio_path: Path | str, threshold: float = 0.5) -> TranscriptResult:
        """Transcribe, diarize, and replace Speaker N with enrolled names when match found."""
        result = self.backend.transcribe(audio_path)
        profiles = self.profile_store.list_all()
        if not profiles:
            return result
        # For each segment, try to identify by embedding if available
        for seg in result.segments:
            if seg.embedding:
                name = self.backend.identify(seg.embedding, profiles, threshold=threshold)
                if name:
                    seg.speaker_id = name
            else:
                # Extract embedding for this segment and try identify
                try:
                    emb = self.backend.extract_embedding(
                        audio_path, start_sec=seg.start_sec, end_sec=seg.end_sec
                    )
                    name = self.backend.identify(emb, profiles, threshold=threshold)
                    if name:
                        seg.speaker_id = name
                except Exception:
                    pass
        return result

    def enroll_speaker(self, name: str, audio_path: Path | str, voice_id: str | None = None) -> VoiceProfile:
        """Enroll a speaker: create voiceprint from reference clip and store."""
        profile = self.backend.enroll(name, audio_path, voice_id=voice_id)
        self.profile_store.add(profile)
        return profile

    def identify_speaker(self, audio_path: Path | str, start_sec: float = 0.0, end_sec: float | None = None) -> str | None:
        """Identify who is speaking in the given audio (or segment). Returns name or None."""
        emb = self.backend.extract_embedding(audio_path, start_sec=start_sec, end_sec=end_sec)
        return self.profile_store.identify(emb)

    def list_speakers(self) -> list[VoiceProfile]:
        """List all enrolled speakers."""
        return self.profile_store.list_all()
