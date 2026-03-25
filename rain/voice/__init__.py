"""Voice: ASR, diarization, voice fingerprinting, speaker identification. Integrates with memory and Vocal Gate."""

from rain.voice.schema import Segment, TranscriptResult, VoiceProfile
from rain.voice.service import VoiceService

__all__ = ["Segment", "TranscriptResult", "VoiceProfile", "VoiceService"]
