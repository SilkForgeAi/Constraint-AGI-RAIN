"""Core intelligence engine — LLM-backed reasoning."""

from __future__ import annotations

import os
import ssl
import sys
import time
from collections.abc import Iterator
from typing import Any

from rain.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    ANTHROPIC_TIMEOUT_SECONDS,
    API_FALLBACK_OLLAMA_MODEL,
    API_FALLBACK_TO_OLLAMA,
    BASE_MODEL_HF,
    BASE_MODEL_HF_SUBDIR,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from rain.core.latency import record as latency_record
from rain.core.backends.anthropic_backend import AnthropicBackend
from rain.core.backends.base import LLMBackend
from rain.core.backends.mlx_backend import MLXBackend
from rain.core.backends.ollama_backend import OllamaBackend
from rain.core.backends.openai_backend import OpenAIBackend


def _is_cloud_transport_failure(exc: BaseException) -> bool:
    """True when failure is likely network/connectivity (safe to retry on local Ollama)."""
    if isinstance(exc, (ConnectionError, TimeoutError, BrokenPipeError, ssl.SSLError)):
        return True
    msg = str(exc).lower()
    needles = (
        "connection",
        "timeout",
        "timed out",
        "network",
        "unreachable",
        "refused",
        "reset by peer",
        "temporary failure",
        "name or service not known",
        "nodename nor servname",
        "ssl",
        "eof",
    )
    return any(n in msg for n in needles)


class CoreEngine:
    """Reasoning core — abstraction over OpenAI/Anthropic/Ollama/MLX."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ):
        # Prefer explicit ctor, then live env (mlx), then rain.config (import-time).
        _env = (os.environ.get("RAIN_LLM_PROVIDER") or "").strip().lower()
        if provider is not None:
            self.provider = str(provider).strip().lower()
        elif _env == "mlx":
            self.provider = "mlx"
        else:
            self.provider = str(LLM_PROVIDER or "ollama").strip().lower()
        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = OPENAI_MODEL
        elif self.provider == "anthropic":
            self.model = ANTHROPIC_MODEL
        elif self.provider == "mlx":
            self.model = BASE_MODEL_HF
        else:
            self.model = OLLAMA_MODEL
        self._backend: LLMBackend = self._build_backend(self.provider, self.model)

    @staticmethod
    def _build_backend(provider: str, model: str) -> LLMBackend:
        p = (provider or "").strip().lower()
        if p == "openai":
            return OpenAIBackend(model=model)
        if p == "anthropic":
            return AnthropicBackend(model=model)
        if p == "mlx":
            return MLXBackend(model=model)
        if p == "ollama":
            return OllamaBackend(model=model)
        raise ValueError(f"Unknown provider: {provider}")

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate completion from message history."""
        start = time.perf_counter()
        if self.provider in ("openai", "anthropic") and (
            (self.provider == "openai" and not OPENAI_API_KEY)
            or (self.provider == "anthropic" and not ANTHROPIC_API_KEY)
        ):
            raise ValueError(
                f"{self.provider.upper()}_API_KEY not set. Add to .env, or use Ollama: install from ollama.com, run 'ollama pull qwen3:14b'"
            )
        try:
            result = self._backend.complete(messages, temperature, max_tokens)
        except Exception as e:
            result = self._maybe_api_fallback(messages, temperature, max_tokens, e)
        ttc_ms = (time.perf_counter() - start) * 1000
        latency_record("complete", time_to_first_token_ms=None, time_to_complete_ms=ttc_ms, provider=self.provider, model=self.model)
        return result

    def _maybe_api_fallback(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        exc: Exception,
    ) -> str:
        """Silent failover to local Ollama when cloud transport fails (optional)."""
        if not API_FALLBACK_TO_OLLAMA or not _is_cloud_transport_failure(exc):
            raise exc
        fb_model = API_FALLBACK_OLLAMA_MODEL or OLLAMA_MODEL
        print(
            "[LOG: Network latency or API transport failure. Switched to Sovereign Local-Inference.]",
            file=sys.stderr,
            flush=True,
        )
        fb = CoreEngine(provider="ollama", model=fb_model)
        return fb._backend.complete(messages, temperature, max_tokens)

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        """Generate completion, yielding text chunks. Records ttft on first yield, ttc when exhausted."""
        start = time.perf_counter()
        ttft_ms: float | None = None

        def _stream() -> Iterator[str]:
            nonlocal ttft_ms
            first = True
            try:
                it = self._backend.complete_stream(messages, temperature, max_tokens)
            except Exception as e:
                # Cloud transport failure? allow one fallback to local.
                if self.provider in ("openai", "anthropic"):
                    fallback_text = self._maybe_api_fallback(messages, temperature, max_tokens, e)
                    it = iter([fallback_text])
                else:
                    raise
            for chunk in it:
                if first:
                    ttft_ms = (time.perf_counter() - start) * 1000
                    first = False
                yield chunk
            ttc_ms = (time.perf_counter() - start) * 1000
            latency_record("complete_stream", time_to_first_token_ms=ttft_ms, time_to_complete_ms=ttc_ms, provider=self.provider, model=self.model)

        yield from _stream()

    def reason(
        self,
        prompt: str,
        context: str = "",
        memory_context: str = "",
    ) -> str:
        """Single reasoning step with context."""
        system = """You are Rain, an AGI cognitive system in development.
You reason clearly, acknowledge uncertainty, and stay helpful and safe.
Use provided context and memory when relevant."""

        content = prompt
        if context:
            content = f"Context:\n{context}\n\nPrompt:\n{prompt}"
        if memory_context:
            content = f"Memory context:\n{memory_context}\n\n{content}"

        return self.complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            temperature=0.6,
        )
