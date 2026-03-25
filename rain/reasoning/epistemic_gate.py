"""
Epistemic gate — halt when semantic entropy is too high (don't guess).
Perfect reasoner fix: if internal disagreement across samples is high, request clarification instead of answering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

DEFAULT_SAMPLES = 3
DEFAULT_AGREE_MIN = 2
HALT_MESSAGE = (
    "My internal uncertainty on this question is too high to give a single reliable answer. "
    "Could you narrow the question, add context, or rephrase so I can answer with confidence?"
)


def _normalize_key(text: str) -> str:
    if not (text or "").strip():
        return ""
    lines = [ln.strip() for ln in (text or "").strip().split("\n") if ln.strip()]
    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i][:120].lower()
        if ln.endswith(".") or "therefore" in ln or "thus" in ln or "answer is" in ln or "result is" in ln:
            return lines[i][:100].strip().lower()
    if lines:
        return lines[-1][:100].strip().lower()
    return (text or "")[:100].strip().lower()


def _keys_agree(k1: str, k2: str, similarity_threshold: float = 0.7) -> bool:
    if not k1 or not k2:
        return bool(k1 == k2)
    if k1 == k2:
        return True
    w1, w2 = set(k1.split()), set(k2.split())
    if not w1 or not w2:
        return False
    overlap = len(w1 & w2) / max(len(w1), len(w2))
    return overlap >= similarity_threshold


def should_halt(
    engine: "CoreEngine",
    messages: list[dict[str, str]],
    num_samples: int = DEFAULT_SAMPLES,
    agree_min: int = DEFAULT_AGREE_MIN,
    max_tokens_per_sample: int = 256,
    existing_response: str | None = None,
) -> tuple[bool, str]:
    if num_samples < 2:
        return False, ""
    keys: list[str] = []
    if existing_response is not None:
        keys.append(_normalize_key(existing_response.strip()))
    for _ in range(num_samples - len(keys)):
        try:
            out = engine.complete(messages, temperature=0.7, max_tokens=max_tokens_per_sample)
            keys.append(_normalize_key((out or "").strip()))
        except Exception:
            keys.append("")
    if not keys:
        return False, ""
    best_count = 0
    for i, k in enumerate(keys):
        if not k:
            continue
        count = sum(1 for j, k2 in enumerate(keys) if j != i and _keys_agree(k, k2))
        if count + 1 > best_count:
            best_count = count + 1
    if best_count >= agree_min:
        return False, ""
    return True, HALT_MESSAGE
