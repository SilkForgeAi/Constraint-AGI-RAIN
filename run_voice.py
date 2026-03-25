#!/usr/bin/env python3
"""
Voice-to-voice mode for Rain with barge-in support.
Run from the AGI Rain project root: python3 run_voice.py
"""

try:
    import eval_type_backport  # noqa: F401
except ImportError:
    pass

import os
import re
import sys
import time
import wave
import tempfile
import subprocess
from collections import deque
from pathlib import Path
from typing import Optional

_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))

try:
    from dotenv import load_dotenv

    load_dotenv(_root / ".env")
    load_dotenv(Path.cwd() / ".env")
except Exception:
    pass

if os.environ.get("ANTHROPIC_API_KEY", "").strip():
    os.environ["RAIN_LLM_PROVIDER"] = "anthropic"
elif os.environ.get("OPENAI_API_KEY", "").strip():
    os.environ["RAIN_LLM_PROVIDER"] = "openai"

# Reduce model-side truncation for long answers in voice mode
os.environ.setdefault("RAIN_MAX_RESPONSE_TOKENS", "4096")

from rain.agent import Rain
from rain.config import VOICE_PROFILES_DB
from rain.memory.voice_profiles import VoiceProfileStore
from rain.voice.backends.whisper_local import get_whisper_backend
from rain.voice.service import VoiceService


def _tts_chunk(text: str, api_key: str, voice_id: str, timeout: int = 240):
    import json
    import urllib.request

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    data = json.dumps({"text": text, "model_id": "eleven_monolingual_v1"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _start_player(path: str):
    cmds = [
        ["afplay", path],
        ["mpv", path, "--no-video", "--really-quiet"],
    ]
    for cmd in cmds:
        try:
            return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
    return None


def _write_float_audio_to_wav(chunks, sample_rate: int):
    import numpy as np

    if not chunks:
        return None
    data = np.concatenate(chunks, axis=0)
    if len(data) < int(sample_rate * 0.25):
        return None
    pcm16 = (data * 32767).clip(-32768, 32767).astype("int16")
    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="rain_barge_")
    os.close(fd)
    out = Path(wav_path)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return out


def _play_mp3_bytes_with_barge(data: bytes, allow_barge: bool = True):
    """Play MP3 and optionally stop playback if user starts speaking.

    Returns a WAV path for captured barge utterance, or None.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(data)
        mp3_path = f.name

    try:
        proc = _start_player(mp3_path)
        if not proc:
            return None

        if not allow_barge:
            proc.wait()
            return None

        try:
            import numpy as np
            import sounddevice as sd
        except Exception:
            proc.wait()
            return None

        sample_rate = 16000
        trigger_threshold = float(os.environ.get("RAIN_BARGE_THRESHOLD", "0.035"))
        trigger_ms = int(os.environ.get("RAIN_BARGE_TRIGGER_MS", "220"))
        end_silence_ms = int(os.environ.get("RAIN_BARGE_END_SILENCE_MS", "700"))
        max_capture_ms = int(os.environ.get("RAIN_BARGE_MAX_MS", "7000"))
        prebuffer_ms = int(os.environ.get("RAIN_BARGE_PREBUFFER_MS", "300"))

        state = {
            "triggered": False,
            "voiced_ms": 0.0,
            "silence_ms": 0.0,
            "captured_ms": 0.0,
            "done": False,
            "chunks": [],
            "pre": deque(maxlen=max(1, int((prebuffer_ms / 1000.0) * sample_rate / 1024))),
        }

        def callback(indata, frames, time_info, status):
            if status:
                return
            frame = indata.copy()
            duration_ms = (frames / float(sample_rate)) * 1000.0
            rms = float(np.sqrt(np.mean(np.square(frame)))) if len(frame) else 0.0

            if not state["triggered"]:
                state["pre"].append(frame)
                if rms >= trigger_threshold:
                    state["voiced_ms"] += duration_ms
                else:
                    state["voiced_ms"] = 0.0
                if state["voiced_ms"] >= trigger_ms:
                    state["triggered"] = True
                    state["chunks"].extend(list(state["pre"]))
                    state["chunks"].append(frame)
                    state["captured_ms"] += duration_ms
            else:
                state["chunks"].append(frame)
                state["captured_ms"] += duration_ms
                if rms < (trigger_threshold * 0.65):
                    state["silence_ms"] += duration_ms
                else:
                    state["silence_ms"] = 0.0
                if state["silence_ms"] >= end_silence_ms or state["captured_ms"] >= max_capture_ms:
                    state["done"] = True

        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=callback,
        )
        stream.start()

        try:
            while proc.poll() is None:
                if state["triggered"]:
                    proc.terminate()
                    break
                time.sleep(0.03)

            if state["triggered"]:
                end_by = time.monotonic() + max(0.5, max_capture_ms / 1000.0)
                while not state["done"] and time.monotonic() < end_by:
                    time.sleep(0.03)
        finally:
            stream.stop()
            stream.close()

        if state["triggered"] and state["chunks"]:
            return _write_float_audio_to_wav(state["chunks"], sample_rate)
        return None
    finally:
        try:
            os.unlink(mp3_path)
        except Exception:
            pass


def _sanitize_for_speech(text: str) -> str:
    """Aggressively remove markdown/symbols so TTS sounds plain conversational."""
    if not text or not text.strip():
        return ""

    t = text
    # Remove fenced code blocks entirely
    t = re.sub(r"```[\s\S]*?```", " ", t)
    # Convert markdown links: [label](url) -> label
    t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)
    # Remove raw URLs
    t = re.sub(r"https?://\S+", " ", t)

    cleaned_lines = []
    for raw in t.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Drop heading markers and list/bullet prefixes
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        # Remove markdown/table/code punctuation tokens commonly read aloud
        line = line.replace("|", " ")
        line = line.replace("**", " ").replace("__", " ")
        line = line.replace("`", " ")
        # Remove leftover heading/bullet characters anywhere
        line = re.sub(r"[#*_~]+", " ", line)
        cleaned_lines.append(line)

    out = " ".join(cleaned_lines)
    # Normalize punctuation spacing and collapse whitespace
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = out.strip()
    return out or text


def speak(text: str, api_key: str, voice_id: str, chunk_chars: int = 1600, timeout: int = 240, retries: int = 3, allow_barge: bool = True):
    """Speak full response; keep continuity and return captured barge utterance if interrupted."""
    if not text or not text.strip():
        return None

    text = _sanitize_for_speech(text)

    # Prefer one synthesis request for smooth single-stream playback.
    for attempt in range(retries):
        audio = _tts_chunk(text, api_key, voice_id, timeout=timeout)
        if audio:
            return _play_mp3_bytes_with_barge(audio, allow_barge=allow_barge)
        time.sleep(1.0 * (attempt + 1))

    # Fallback: synthesize chunks, merge bytes, play once (still continuous).
    chunks = []
    rest = text.strip()
    while rest:
        if len(rest) <= chunk_chars:
            chunks.append(rest)
            break
        segment = rest[:chunk_chars]
        cut = max(segment.rfind('.'), segment.rfind('\n'))
        if cut > chunk_chars // 2:
            chunks.append(segment[: cut + 1].strip())
            rest = rest[cut + 1 :].lstrip()
        else:
            chunks.append(segment.strip())
            rest = rest[chunk_chars:].lstrip()

    mp3_parts = []
    for chunk in chunks:
        if not chunk:
            continue
        chunk_audio = None
        for attempt in range(retries):
            chunk_audio = _tts_chunk(chunk, api_key, voice_id, timeout=timeout)
            if chunk_audio:
                break
            time.sleep(1.0 * (attempt + 1))
        if chunk_audio:
            mp3_parts.append(chunk_audio)

    if not mp3_parts:
        print('TTS failed after retries.', file=sys.stderr)
        return None

    merged = b''.join(mp3_parts)
    return _play_mp3_bytes_with_barge(merged, allow_barge=allow_barge)

def record_once(sample_rate: int = 16000):
    try:
        import numpy as np
        import sounddevice as sd
    except Exception:
        print("Missing mic deps. Install: python3 -m pip install sounddevice numpy", file=sys.stderr)
        return None

    input("\nPress Enter to START recording...")
    print("Recording... press Enter to STOP.")

    chunks = []

    def callback(indata, frames, time_info, status):
        if status:
            return
        chunks.append(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=callback,
        )
        stream.start()
        input()
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"Mic error: {e}", file=sys.stderr)
        return None

    if not chunks:
        print("No audio captured.")
        return None

    data = np.concatenate(chunks, axis=0)
    if len(data) < int(sample_rate * 0.2):
        print("Audio too short.")
        return None
    pcm16 = (data * 32767).clip(-32768, 32767).astype("int16")

    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="rain_voice_")
    os.close(fd)
    path = Path(wav_path)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return path


def _transcribe_file(service: VoiceService, wav_path: Path) -> str:
    try:
        result = service.transcribe_and_identify(wav_path)
        return (result.full_text or "").strip()
    except Exception as e:
        print(f"Transcription error: {e}", file=sys.stderr)
        return ""


def _looks_truncated(text: str) -> bool:
    tail = (text or "").strip()
    if len(tail) < 220:
        return False
    if tail.endswith(("...", "…", "—", ":", ";", "(", "[", "{")):
        return True
    return not tail.endswith((".", "!", "?", "\"", "'", ")", "]", "}"))


def _complete_response(rain: Rain, prompt: str, response: str, history: list[dict]) -> str:
    """If a response appears token-truncated, auto-request continuation."""
    full = (response or "").strip()
    for _ in range(2):
        if not _looks_truncated(full):
            break
        continue_prompt = (
            "Continue your previous answer from exactly where it stopped. "
            "Do not restart or repeat prior sections. Finish the answer completely."
        )
        try:
            cont = rain.think(
                continue_prompt,
                use_tools=False,
                use_memory=False,
                history=history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": full},
                ],
                memory_namespace="chat",
            )
        except Exception:
            break
        cont = (cont or "").strip()
        if not cont:
            break
        full = f"{full}\n{cont}"
    return full


def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if not api_key or not voice_id:
        print("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env.", file=sys.stderr)
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("Set ANTHROPIC_API_KEY in .env for Rain.", file=sys.stderr)
        sys.exit(1)

    backend = get_whisper_backend()
    if not backend:
        print("Whisper not available. Install: python3 -m pip install openai-whisper", file=sys.stderr)
        print("If needed: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    service = VoiceService(backend, VoiceProfileStore(VOICE_PROFILES_DB))
    rain = Rain()
    history = []
    pending_prompt = None

    print("Rain voice-to-voice ready.")
    print("Memory is OFF for speed in this run.")
    print("Barge-in is OFF: Rain will always finish speaking.")
    print("Say 'bye' or 'exit' to quit.")

    while True:
        if pending_prompt is None:
            wav_path = record_once()
            if not wav_path:
                continue
            try:
                prompt = _transcribe_file(service, wav_path)
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            prompt = pending_prompt
            pending_prompt = None

        if not prompt:
            print("I didn't catch that. Try again.")
            continue

        print(f"You said: {prompt}")
        if prompt.lower() in ("bye", "exit", "quit"):
            print("Bye.")
            break

        print("Thinking...", flush=True)
        try:
            response = rain.think(
                prompt,
                use_tools=False,
                use_memory=False,
                history=history,
                memory_namespace="chat",
            )
            response = _complete_response(rain, prompt, response, history)
        except Exception as e:
            print(f"Rain error: {e}", file=sys.stderr)
            continue

        clean_response = _sanitize_for_speech(response)
        print(f"Rain> {clean_response}")
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": clean_response})
        if len(history) > 20:
            history = history[-20:]

        barge_wav = speak(
            clean_response,
            api_key,
            voice_id,
            chunk_chars=1600,
            timeout=240,
            retries=3,
            allow_barge=False,
        )

        if False and barge_wav:
            try:
                barged_prompt = _transcribe_file(service, barge_wav)
            finally:
                try:
                    barge_wav.unlink(missing_ok=True)
                except Exception:
                    pass

            if barged_prompt:
                print(f"You interrupted: {barged_prompt}")
                if barged_prompt.lower() in ("bye", "exit", "quit"):
                    print("Bye.")
                    break
                pending_prompt = barged_prompt


if __name__ == "__main__":
    main()
