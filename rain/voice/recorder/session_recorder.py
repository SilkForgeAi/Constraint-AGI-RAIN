"""Session recorder: record audio during active sessions only; hash-chain to audit; ADOM ingest."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rain.config import (
    ADOM_INGEST_URL,
    SESSION_ANNOUNCE,
    SESSION_IDLE_TIMEOUT,
    SESSION_STORE,
)
from rain.voice.recorder.session_store import SessionStore


def _compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


class SessionRecorder:
    """Records audio from session start to stop; idle timeout auto-closes. Hash-chains to audit."""

    def __init__(
        self,
        store: SessionStore,
        audit_log: Any,
        *,
        idle_timeout_seconds: int | None = None,
        announce: bool | None = None,
        adom_url: str | None = None,
    ):
        self._store = store
        self._audit = audit_log
        self._idle_timeout = idle_timeout_seconds if idle_timeout_seconds is not None else SESSION_IDLE_TIMEOUT
        self._announce = announce if announce is not None else SESSION_ANNOUNCE
        self._adom_url = adom_url or ADOM_INGEST_URL or ""
        self._session_id: str | None = None
        self._start_time: str | None = None
        self._speaker_name: str | None = None
        self._speaker_id: str | None = None
        self._last_activity: float = 0.0
        self._vocal_gate_events: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._chunks: list[Any] = []
        self._stream = None
        self._sample_rate = 16000

    def start_session(self, speaker_name: str | None = None, speaker_id: str | None = None) -> str:
        with self._lock:
            if self._session_id:
                return self._session_id
            self._session_id = str(uuid.uuid4())[:12]
            self._start_time = datetime.now(timezone.utc).isoformat()
            self._speaker_name = speaker_name or "unknown"
            self._speaker_id = speaker_id or "unknown"
            self._last_activity = time.monotonic()
            self._vocal_gate_events = []
            self._chunks = []
            self._stream = None
        if self._announce:
            self._play_session_marker("open")
        self._start_recording()
        return self._session_id

    def _play_session_marker(self, kind: str) -> None:
        """Audible or visible marker. Open: 'Session open, [timestamp], Speaker: [name].' Close: 'Session closed, [timestamp].'"""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if kind == "open":
            msg = f"Session open, {ts}, Speaker: {self._speaker_name or 'unknown'}."
        else:
            msg = f"Session closed, {ts}."
        try:
            import sys
            print(f"  [Session] {msg}", flush=True)
        except Exception:
            pass
        try:
            import sounddevice as sd
            from math import pi, sin
            duration = 0.15
            n = int(duration * self._sample_rate)
            t = [0.3 * sin(2 * pi * 440 * i / self._sample_rate) for i in range(n)]
            import array
            arr = array.array("f", t)
            sd.play(arr, self._sample_rate)
            sd.wait()
        except Exception:
            pass

    def _start_recording(self) -> None:
        try:
            import sounddevice as sd
            import numpy as np
            self._chunks = []

            def callback(indata, frames, time_info, status):
                if status:
                    return
                self._chunks.append(indata.copy())

            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=callback,
            )
            self._stream.start()
        except Exception:
            self._stream = None
            self._chunks = []

    def stop_session(self, transcript_available: bool = False) -> str | None:
        with self._lock:
            sid = self._session_id
            if not sid:
                return None
            start = self._start_time
            speaker_name = self._speaker_name or "unknown"
            speaker_id = self._speaker_id or "unknown"
            vocal_events = list(self._vocal_gate_events)
            self._session_id = None
            self._start_time = None
            self._speaker_name = None
            self._speaker_id = None
            self._vocal_gate_events = []

        if self._announce:
            self._play_session_marker("close")

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        end_time = datetime.now(timezone.utc).isoformat()
        timestamp_fs = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        wav_path, json_path = self._store.session_file_paths(sid, timestamp_fs, speaker_name)

        duration_seconds = 0.0
        file_hash = ""
        try:
            import numpy as np
            if self._chunks:
                data = np.concatenate(self._chunks, axis=0)
                duration_seconds = len(data) / self._sample_rate
                # float32 -> int16 for WAV
                data = (data * 32767).clip(-32768, 32767).astype("int16")
                import wave
                wav_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(wav_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self._sample_rate)
                    wf.writeframes(data.tobytes())
                file_hash = _compute_file_hash(wav_path)
        except Exception:
            pass

        metadata = {
            "session_id": sid,
            "start_time": start,
            "end_time": end_time,
            "speaker_name": speaker_name,
            "speaker_id": speaker_id,
            "duration_seconds": round(duration_seconds, 2),
            "file_hash": file_hash,
            "vocal_gate_events": vocal_events,
            "transcript_available": transcript_available,
        }
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        self._store.add_session(
            session_id=sid,
            start_time=start,
            end_time=end_time,
            speaker_name=speaker_name,
            speaker_id=speaker_id,
            wav_path=str(wav_path),
            json_path=str(json_path),
            file_hash=file_hash,
            duration_seconds=duration_seconds,
        )

        self._audit.log(
            "session_recorder",
            {
                "session_id": sid,
                "audio_hash": file_hash,
                "speaker_name": speaker_name,
                "speaker_id": speaker_id,
                "duration_seconds": duration_seconds,
                "wav_path": str(wav_path),
                "linked_audit": "chain",
            },
            outcome="ok",
        )

        if self._adom_url:
            try:
                import urllib.request
                payload = json.dumps({
                    "source": "rain_session_recorder",
                    "session_id": sid,
                    "speaker": speaker_name,
                    "audio_hash": file_hash,
                    "duration_seconds": duration_seconds,
                    "transcript_available": transcript_available,
                }).encode("utf-8")
                req = urllib.request.Request(
                    self._adom_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass

        return sid

    def record_vocal_gate_block(self, action_attempted: str, speaker: str) -> None:
        with self._lock:
            if not self._session_id:
                return
            self._vocal_gate_events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "vocal_gate_block",
                "action_attempted": action_attempted[:500],
                "speaker": speaker,
            })

    def is_recording(self) -> bool:
        with self._lock:
            return self._session_id is not None

    def reset_idle(self) -> None:
        with self._lock:
            self._last_activity = time.monotonic()

    def get_idle_seconds(self) -> float:
        with self._lock:
            if not self._session_id:
                return 0.0
            return time.monotonic() - self._last_activity

    def get_idle_timeout(self) -> int:
        return self._idle_timeout

    def update_speaker(self, speaker_name: str | None = None, speaker_id: str | None = None) -> None:
        with self._lock:
            if speaker_name is not None:
                self._speaker_name = speaker_name
            if speaker_id is not None:
                self._speaker_id = speaker_id
