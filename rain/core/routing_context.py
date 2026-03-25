"""Context for hybrid LLM routing (local default → API for heavy/sovereign turns)."""

from __future__ import annotations

from contextvars import ContextVar, Token

_current_prompt: ContextVar[str | None] = ContextVar("rain_routing_prompt", default=None)


def push_routing_prompt(prompt: str) -> Token:
    return _current_prompt.set((prompt or "").strip() or None)


def pop_routing_prompt(token: Token) -> None:
    _current_prompt.reset(token)


def get_routing_prompt() -> str | None:
    return _current_prompt.get()
