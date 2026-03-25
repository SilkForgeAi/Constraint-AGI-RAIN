"""
Tier 3: Known/inferred labels — provenance for claims.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

def _inferred_phrases() -> tuple[str, ...]:
    return ("I conclude", "therefore", "thus", "so we have", "it follows", "this suggests", "likely", "implies")

def _known_phrases() -> tuple[str, ...]:
    return ("according to", "as stated in", "the document says", "it is known that", "fact:", "source:")

def tag_sentences_heuristic(response: str) -> list[tuple[str, str]]:
    """Tag sentences as known or inferred by phrase heuristics. Returns [(snippet, "known"|"inferred")]."""
    if not (response or "").strip():
        return []
    r = (response or "").strip()
    sentences = re.findall(r"[A-Z][^.!?]*[.!?]", r)
    out: list[tuple[str, str]] = []
    for s in sentences:
        s = s.strip()
        low = s.lower()
        if any(p in low for p in _known_phrases()):
            out.append((s[:200], "known"))
        elif any(p in low for p in _inferred_phrases()):
            out.append((s[:200], "inferred"))
        else:
            out.append((s[:200], "inferred"))
    return out

def format_response_with_labels(response: str, tags: list[tuple[str, str]] | None = None) -> str:
    """Prepend a short provenance line if we have tags. Does not rewrite full response."""
    if tags is None:
        tags = tag_sentences_heuristic(response)
    known_count = sum(1 for _, l in tags if l == "known")
    inferred_count = sum(1 for _, l in tags if l == "inferred")
    if known_count + inferred_count == 0:
        return response
    prefix = f"[Provenance: {known_count} known, {inferred_count} inferred.] "
    if not response.startswith("["):
        return prefix + response
    return response
