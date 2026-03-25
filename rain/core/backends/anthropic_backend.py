from __future__ import annotations

import os
import time
from collections.abc import Iterator

from rain.config import ANTHROPIC_API_KEY, ANTHROPIC_TIMEOUT_SECONDS
from rain.core.backends.base import retry_call


def _is_transient_anthropic_error(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    msg = str(exc)
    return (status in (429, 500, 502, 503, 529)) or ("Error code: 500" in msg) or ("Internal server error" in msg)


class AnthropicBackend:
    provider = "anthropic"

    def __init__(self, *, model: str):
        self.model = model

    def _client(self, *, max_tokens: int):
        try:
            import anthropic
        except ImportError as e:
            raise ImportError("Install anthropic: pip install anthropic") from e
        base_timeout = float(os.environ.get("RAIN_ANTHROPIC_TIMEOUT_SECONDS", str(ANTHROPIC_TIMEOUT_SECONDS)))
        timeout = max(base_timeout, 120.0 + max_tokens * 0.02)
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=timeout)

    @staticmethod
    def _split_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
        system = ""
        chat: list[dict[str, str]] = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                chat.append({"role": m["role"], "content": m["content"]})
        return system, chat

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        client = self._client(max_tokens=max_tokens)
        system, chat = self._split_messages(messages)

        def _call():
            return client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=chat,
                temperature=temperature,
            )

        resp = retry_call(_call, is_transient=_is_transient_anthropic_error)
        text = ""
        for b in resp.content:
            if hasattr(b, "text"):
                text += b.text
        return text.strip()

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        client = self._client(max_tokens=max_tokens)
        system, chat = self._split_messages(messages)

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                with client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=chat,
                    temperature=temperature,
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except Exception as e:
                last_err = e
                if (not _is_transient_anthropic_error(e)) or attempt >= 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise last_err  # type: ignore[misc]

