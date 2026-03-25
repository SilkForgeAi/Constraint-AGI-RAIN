"""Backend abstraction and shared retry helpers."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar


class LLMBackend(Protocol):
    provider: str
    model: str

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str: ...

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]: ...


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_sleep_s: float = 1.5


def retry_call(
    fn: Callable[[], T],
    *,
    is_transient: Callable[[BaseException], bool],
    policy: RetryPolicy = RetryPolicy(),
) -> T:
    last: BaseException | None = None
    for attempt in range(policy.max_attempts):
        try:
            return fn()
        except BaseException as e:
            last = e
            if (not is_transient(e)) or attempt >= policy.max_attempts - 1:
                raise
            time.sleep(policy.base_sleep_s * (attempt + 1))
    raise last  # type: ignore[misc]

