from __future__ import annotations

import ssl
import time
from collections.abc import Iterator

from rain.config import OLLAMA_BASE_URL


class OllamaBackend:
    provider = "ollama"

    def __init__(self, *, model: str):
        self.model = model

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Ollama local API — no API key needed.

        Some Ollama models only support the legacy /completions endpoint.
        If chat completions are not supported, fall back to /completions.
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai (used for Ollama)") from e

        last_err: BaseException | None = None
        for attempt in range(3):
            try:
                client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=300.0)
                try:
                    resp = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=min(max_tokens, 4096),
                    )
                    return (resp.choices[0].message.content or "").strip()
                except Exception as e:
                    if "does not support chat" not in str(e).lower():
                        raise

                prompt_parts: list[str] = []
                for m in messages:
                    role = (m.get("role") or "").lower()
                    content = (m.get("content") or "").strip()
                    if not content:
                        continue
                    if role == "system":
                        prompt_parts.append(f"System: {content}")
                    elif role == "user":
                        prompt_parts.append(f"User: {content}")
                    elif role == "assistant":
                        prompt_parts.append(f"Assistant: {content}")
                    else:
                        prompt_parts.append(content)
                prompt_parts.append("Assistant:")
                prompt = "\n".join(prompt_parts).strip()

                resp = client.completions.create(
                    model=self.model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 4096),
                )
                return (resp.choices[0].text or "").strip()
            except (ssl.SSLError, OSError, ConnectionError) as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise last_err  # type: ignore[misc]

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        """Ollama local API streaming.

        Some Ollama models do not support OpenAI-style chat completions.
        When that happens, fall back to the legacy /completions endpoint.
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai (used for Ollama)") from e

        last_err: BaseException | None = None
        for attempt in range(3):
            try:
                client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=300.0)
                try:
                    stream = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=min(max_tokens, 4096),
                        stream=True,
                    )
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                    return
                except Exception as e:
                    if "does not support chat" not in str(e).lower():
                        raise

                prompt_parts: list[str] = []
                for m in messages:
                    role = (m.get("role") or "").lower()
                    content = (m.get("content") or "").strip()
                    if not content:
                        continue
                    if role == "system":
                        prompt_parts.append(f"System: {content}")
                    elif role == "user":
                        prompt_parts.append(f"User: {content}")
                    elif role == "assistant":
                        prompt_parts.append(f"Assistant: {content}")
                    else:
                        prompt_parts.append(content)
                prompt_parts.append("Assistant:")
                prompt = "\n".join(prompt_parts).strip()

                resp = client.completions.create(
                    model=self.model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 4096),
                )
                text = resp.choices[0].text or ""
                if text:
                    yield text
                return
            except (ssl.SSLError, OSError, ConnectionError) as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise last_err  # type: ignore[misc]

