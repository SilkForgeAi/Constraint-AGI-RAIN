from __future__ import annotations

from collections.abc import Iterator

from rain.config import OPENAI_API_KEY


class OpenAIBackend:
    provider = "openai"

    def __init__(self, *, model: str):
        self.model = model

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai") from e
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai") from e
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

