"""Optional second CoreEngine (API) for high-stakes prompts while default stays local."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rain.core.engine import CoreEngine

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class RoutingCoreEngine:
    """Delegates to a stronger (API) engine when hybrid rules apply; else default."""

    __slots__ = ("_default", "_strong", "_routing_prompt")

    def __init__(self, default: CoreEngine, strong: CoreEngine | None) -> None:
        self._default = default
        self._strong = strong
        self._routing_prompt: str | None = None

    def set_routing_prompt(self, prompt: str | None) -> None:
        self._routing_prompt = (prompt or "").strip() or None

    def _pick(self, max_tokens: int) -> CoreEngine:
        from rain.core.routing_context import get_routing_prompt
        from rain.hybrid_config import should_route_to_hybrid_llm

        prompt = self._routing_prompt or get_routing_prompt() or ""
        if self._strong and should_route_to_hybrid_llm(prompt, max_tokens):
            logger.debug(
                "hybrid_llm: routing to strong model provider=%s model=%s",
                self._strong.provider,
                self._strong.model,
            )
            return self._strong
        return self._default

    @property
    def provider(self) -> str:
        return self._default.provider

    @property
    def model(self) -> str:
        return self._default.model

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        eng = self._pick(max_tokens)
        return eng.complete(messages, temperature=temperature, max_tokens=max_tokens)

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Any:
        eng = self._pick(max_tokens)
        return eng.complete_stream(messages, temperature=temperature, max_tokens=max_tokens)

    def reason(self, prompt: str, context: str = "", memory_context: str = "") -> str:
        """Delegate to default engine (single-shot helper)."""
        return self._default.reason(prompt, context=context, memory_context=memory_context)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._default, name)


def build_routing_engine() -> CoreEngine | RoutingCoreEngine:
    """Return default CoreEngine, or RoutingCoreEngine when hybrid is configured."""
    from rain.hybrid_config import build_strong_hybrid_engine

    default = CoreEngine()
    strong = build_strong_hybrid_engine()
    if strong is None:
        return default
    return RoutingCoreEngine(default, strong)
