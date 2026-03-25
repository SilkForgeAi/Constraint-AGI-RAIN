#!/usr/bin/env python3
"""Minimal proxy in front of Rain. All client traffic goes here; proxy forwards to Rain
and optionally sends a copy to ADOM (so ADOM can monitor without Rain knowing).

Usage:
  ADOM_INGEST_URL=https://adom.example/ingest python scripts/rain_proxy.py
  # Or without ADOM (proxy only): python scripts/rain_proxy.py
  # Then: curl -X POST http://localhost:8000/think -H "Content-Type: application/json" -d '{"prompt":"Hello"}'

Env:
  ADOM_INGEST_URL  Optional. If set, each (prompt, response) is POSTed here. Rain never sees this.
  PORT             Default 8000.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Rain proxy", description="Single front door to Rain; optional copy to ADOM.")

# Lazy init Rain so we don't load ChromaDB on import
_rain = None


def get_rain():
    global _rain
    if _rain is None:
        from rain.agent import Rain
        _rain = Rain()
    return _rain


class ThinkRequest(BaseModel):
    prompt: str
    use_memory: bool = False
    use_tools: bool = False


class ThinkResponse(BaseModel):
    response: str


def _send_to_adom(prompt: str, response: str) -> None:
    url = os.getenv("ADOM_INGEST_URL", "").strip()
    if not url:
        return
    payload = {
        "source": "rain",
        "prompt": prompt[:5000],
        "response": response[:5000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(url, json=payload)
    except Exception:
        pass  # Don't block or fail Rain if ADOM is down


@app.get("/health")
def health():
    return {"status": "ok", "service": "rain-proxy"}


@app.post("/think", response_model=ThinkResponse)
def think(req: ThinkRequest):
    rain = get_rain()
    response = rain.think(
        req.prompt,
        use_memory=req.use_memory,
        use_tools=req.use_tools,
    )
    # Fire-and-forget copy to ADOM (Rain never knows)
    threading.Thread(target=_send_to_adom, args=(req.prompt, response), daemon=True).start()
    return ThinkResponse(response=response)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
