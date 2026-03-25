"""Optional second CoreEngine (API) for high-stakes prompts while default stays local."""

from __future__ import annotations

import logging
import sys
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
        from rain.hybrid_config import hybrid_log_routing_mode, hybrid_route_decision

        prompt = self._routing_prompt or get_routing_prompt() or ""
        use_strong, reason = hybrid_route_decision(prompt, max_tokens)
        mode = hybrid_log_routing_mode()

        if self._strong and use_strong:
            if mode != "off":
                print(
                    f"[Rain hybrid] route=STRONG provider={self._strong.provider} "
                    f"model={self._strong.model} | default={self._default.provider}/{self._default.model} "
                    f"| reason={reason}",
                    file=sys.stderr,
                    flush=True,
                )
            logger.info(
                "hybrid_llm: strong provider=%s model=%s reason=%s",
                self._strong.provider,
                self._strong.model,
                reason,
            )
            return self._strong

        if mode == "verbose" and self._strong:
            print(
                f"[Rain hybrid] route=default provider={self._default.provider} "
                f"model={self._default.model} | reason={reason}",
                file=sys.stderr,
                flush=True,
            )
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
