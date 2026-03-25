"""Scale and efficiency — response cache, context caps. Build support for human-ballpark efficiency."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

# Max cache entries (LRU eviction)
RESPONSE_CACHE_MAX = 100


class ResponseCache:
    """LRU cache for prompt -> response. Key = hash(prompt_prefix). Config-gated; buyer can enable."""

    def __init__(self, max_size: int = RESPONSE_CACHE_MAX) -> None:
        self._cache: OrderedDict[int, str] = OrderedDict()
        self._max_size = max_size

    def _key(self, prompt: str, prefix_len: int = 500) -> int:
        return hash((prompt[:prefix_len],))

    def get(self, prompt: str) -> str | None:
        k = self._key(prompt)
        if k not in self._cache:
            return None
        self._cache.move_to_end(k)
        return self._cache[k]

    def set(self, prompt: str, response: str) -> None:
        k = self._key(prompt)
        if k in self._cache:
            self._cache.move_to_end(k)
        self._cache[k] = response
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()
