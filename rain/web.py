"""Rain web UI — FastAPI chat server."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from rain.agent import Rain
from rain.config import RAIN_ROOT, WEB_API_KEY
from rain.health import health_check

app = FastAPI(title="Rain")
rain = Rain()


def _stream_events(chunks):
    """Generate SSE events from text chunks."""
    for chunk in chunks:
        # Escape newlines for SSE data
        data = chunk.replace("\n", "\ndata: ").replace("\r", "")
        yield f"data: {data}\n\n"


def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """If WEB_API_KEY is set, require matching X-API-Key header."""
    if not WEB_API_KEY:
        return
    if not x_api_key or x_api_key != WEB_API_KEY:
        raise HTTPException(401, "Invalid or missing API key")


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []
    use_memory: bool = False
    use_tools: bool = False


class ChatResponse(BaseModel):
    response: str
    history: list[dict[str, str]]


@app.get("/health")
async def health():
    """Validate config; no secrets. Returns 200 + message or 503 on failure."""
    ok, msg = health_check()
    if ok:
        return {"status": "ok", "message": msg}
    from fastapi.responses import JSONResponse
    return JSONResponse(content={"status": "unhealthy", "message": msg}, status_code=503)


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (RAIN_ROOT / "rain" / "static" / "index.html").read_text(encoding="utf-8")
    return html


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _: None = Depends(_require_api_key)):
    if not req.message.strip():
        raise HTTPException(400, "Empty message")
    try:
        response = rain.think(
            req.message,
            use_memory=req.use_memory,
            use_tools=req.use_tools,
            history=req.history,
            memory_namespace="chat" if req.use_memory else None,
        )
        history = req.history + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": response},
        ]
        if len(history) > 20:
            history = history[-20:]
        return ChatResponse(response=response, history=history)
    except Exception as e:
        raise HTTPException(500, str(e))


class ChatStreamRequest(ChatRequest):
    """Same as ChatRequest for streaming."""


@app.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest, _: None = Depends(_require_api_key)):
    """Stream chat response as SSE. Use when use_tools=False for true streaming."""
    if not req.message.strip():
        raise HTTPException(400, "Empty message")
    try:
        chunks = rain.think_stream(
            req.message,
            use_memory=req.use_memory,
            use_tools=req.use_tools,
            history=req.history,
            memory_namespace="chat" if req.use_memory else None,
        )
        return StreamingResponse(
            _stream_events(chunks),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        raise HTTPException(500, str(e))


def run_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
