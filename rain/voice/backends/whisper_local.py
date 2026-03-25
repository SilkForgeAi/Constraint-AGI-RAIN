"""Local Whisper ASR backend. Optional: diarization via pyannote when available."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from rain.voice.backends.base import VoiceBackend
from rain.voice.schema import Segment, TranscriptResult

# Lazy global caches for models (None = not loaded, loaded value = model instance)
_faster_whisper_model: Optional[object] = None
_whisper_model: Optional[object] = None


def _get_faster_whisper_model():
    """Load and cache faster-whisper model. Returns None if not available."""
    global _faster_whisper_model
    if _faster_whisper_model is not None:
        return _faster_whisper_model
    try:
        from faster_whisper import WhisperModel
        model_size = os.environ.get("RAIN_FAST_WHISPER_MODEL", "small.en")
        device = os.environ.get("RAIN_FAST_WHISPER_DEVICE", "auto")
        compute_type = os.environ.get("RAIN_FAST_WHISPER_COMPUTE_TYPE", "int8")
        _faster_whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        return _faster_whisper_model
    except Exception:
        return None


def _get_whisper_model():
    """Load and cache openai-whisper model. Returns None if not available."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        import whisper
        _whisper_model = whisper.load_model("base")
        return _whisper_model
    except Exception:
        return None


def _transcribe_faster_whisper(audio_path: Path) -> Tuple[str, list]:
    """Transcribe using faster-whisper. Returns (full_text, [(start, end, text), ...]) or ("", [])."""
    model = _get_faster_whisper_model()
    if model is None:
        return "", []
    try:
        language = os.environ.get("RAIN_FAST_WHISPER_LANGUAGE", "en")
        beam_size = int(os.environ.get("RAIN_FAST_WHISPER_BEAM_SIZE", "1"))
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            vad_filter=True,
            word_timestamps=False,
        )
        segs = []
        parts = []
        for seg in segments_iter:
            start = float(seg.start)
            end = float(seg.end)
            text = (seg.text or "").strip()
            segs.append((start, end, text))
            if text:
                parts.append(text)
        full_text = " ".join(parts).strip()
        if not segs and full_text:
            segs = [(0.0, 1.0, full_text)]
        return full_text, segs
    except Exception:
        return "", []


def _transcribe_whisper(audio_path: Path) -> Tuple[str, list]:
    """Transcribe using openai-whisper. Returns (full_text, [(start, end, text), ...]) or ("", [])."""
    model = _get_whisper_model()
    if model is None:
        return "", []
    try:
        result = model.transcribe(str(audio_path), word_timestamps=False)
        text = (result.get("text") or "").strip()
        segs = []
        for s in (result.get("segments") or []):
            start = float(s.get("start", 0))
            end = float(s.get("end", start + 1))
            segs.append((start, end, (s.get("text") or "").strip()))
        if not segs and text:
            segs = [(0.0, 1.0, text)]
        return text, segs
    except Exception:
        return "", []


def _try_whisper_transcribe(audio_path: Path) -> Tuple[str, list]:
    """Return (full_text, [(start, end, text), ...]). Tries faster-whisper first, then whisper."""
    text, segs = _transcribe_faster_whisper(audio_path)
    if not text and not segs:
        text, segs = _transcribe_whisper(audio_path)
    return text, segs


def _try_pyannote_diarize(audio_path: Path) -> list:
    """Return [(start, end, "Speaker 0"), ...]. Empty if pyannote not available."""
    try:
        from pyannote.audio import Pipeline
        import os
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        if not token:
            return []
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=token)
        diar = pipeline(str(audio_path))
        return [(seg.start, seg.end, seg.speaker) for seg in diar.itertracks(yield_label=True)]
    except Exception:
        return []


class WhisperLocalBackend(VoiceBackend):
    """Uses Whisper for ASR; optionally pyannote for diarization. Fallback: single segment."""

    def transcribe(self, audio_path: Path | str) -> TranscriptResult:
        path = Path(audio_path)
        if not path.exists():
            return TranscriptResult(full_text="", segments=[])
        text, asr_segs = _try_whisper_transcribe(path)
        diar = _try_pyannote_diarize(path)
        segments = []
        if diar and asr_segs:
            # Align ASR segments to diarization (simple: assign each ASR segment to nearest speaker)
            for start, end, seg_text in asr_segs:
                best_speaker = "Speaker 0"
                mid = (start + end) / 2
                for d_start, d_end, sp in diar:
                    if d_start <= mid <= d_end:
                        best_speaker = sp
                        break
                segments.append(Segment(start_sec=start, end_sec=end, speaker_id=best_speaker, text=seg_text))
        elif asr_segs:
            for start, end, seg_text in asr_segs:
                segments.append(Segment(start_sec=start, end_sec=end, speaker_id="Speaker 0", text=seg_text))
        if not segments and text:
            segments = [Segment(0.0, 1.0, "Speaker 0", text)]
        return TranscriptResult(full_text=text, segments=segments)

    def extract_embedding(self, audio_path: Path | str, start_sec: float = 0.0, end_sec: Optional[float] = None) -> list:
        """Use resemblyzer or speechbrain if available; else deterministic from path."""
        try:
            from resemblyzer import preprocess_wav, VoiceEncoder
            from pathlib import Path
            import numpy as np
            path = Path(audio_path)
            wav = preprocess_wav(path)
            encoder = VoiceEncoder()
            emb = encoder.embed_utterance(wav)
            return emb.tolist()
        except Exception:
            pass
        path = str(audio_path)
        h = sum(ord(c) for c in path) % 1000
        return [0.01 * (h + i) for i in range(192)]


def get_whisper_backend() -> Optional[WhisperLocalBackend]:
    """Return WhisperLocalBackend if faster_whisper or whisper is available, else None."""
    if _get_faster_whisper_model() is not None:
        return WhisperLocalBackend()
    if _get_whisper_model() is not None:
        return WhisperLocalBackend()
    return None
