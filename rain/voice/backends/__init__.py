"""Voice backends: mock and real (whisper/pyannote when available)."""

from rain.voice.backends.base import VoiceBackend
from rain.voice.backends.mock import MockVoiceBackend

__all__ = ["VoiceBackend", "MockVoiceBackend"]
