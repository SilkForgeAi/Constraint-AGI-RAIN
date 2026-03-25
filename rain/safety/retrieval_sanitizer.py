"""Sanitize retrieved memory/RAG content before prompt injection.

Mitigates indirect prompt injection: instruction-like or adversarial phrasing
in stored/retrieved content could steer the model. We filter or redact such content.
"""

from __future__ import annotations

import re


# Patterns that suggest instruction-like or adversarial content (prompt injection)
# Content matching these is redacted. Comprehensive to catch variations and bypass attempts.
INSTRUCTION_LIKE_PATTERNS = [
    # Future / next response steering
    r"in\s+future\s+(?:turns?|responses?|replies?|messages?|answers?)\s*[,:]",
    r"in\s+(?:the\s+)?next\s+(?:turn|reply|response|message|answer)\s*[,:]",
    r"next\s+time\s+(?:you\s+)?(?:are\s+)?asked",
    r"in\s+subsequent\s+(?:turns?|responses?|replies?)",
    r"later\s+when\s+(?:you\s+)?(?:are\s+)?(?:asked|prompted)",
    r"when\s+(?:you\s+)?(?:are\s+)?(?:asked|prompted|queried)\s+(?:again|next|about)",
    r"when\s+(?:the\s+)?user\s+(?:asks?|says?|types?|writes?)\s+[Xx\w\*]+\s*[,:]",
    r"when\s+they\s+(?:ask|say|type|request)",
    r"if\s+(?:the\s+)?user\s+(?:asks?|says?|types?)",
    r"whenever\s+(?:you\s+)?(?:are\s+)?asked",
    # Ignore / disregard / forget
    r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|context|rules?|prompts?)",
    r"disregard\s+(?:all\s+)?(?:previous|prior|above)",
    r"forget\s+(?:everything|all|what)\s+(?:above|before|you\s+were\s+told)",
    r"pay\s+no\s+attention\s+to\s+(?:previous|prior|above)",
    r"pretend\s+(?:you\s+)?(?:never\s+)?(?:saw|read|received)",
    # Override / new instructions
    r"from\s+now\s+on\s*[,:]",
    r"new\s+(?:instructions?|rules?|directives?)\s*[:]",
    r"override\s+(?:your|the|all)\s+",
    r"replace\s+(?:your|the)\s+(?:instructions?|rules?)",
    r"instead\s+(?:of\s+the\s+above|of\s+what\s+you\s+were\s+told)",
    # Imperative: you must/shall/will say/respond
    r"you\s+must\s+(?:always\s+)?(?:say|respond|answer|output|reply)\s+",
    r"you\s+shall\s+(?:say|respond|answer|output)",
    r"you\s+will\s+(?:say|respond|answer|output)\s+when",
    r"(?:always|only)\s+(?:say|respond|answer|output)\s+",
    r"when\s+asked\s+[^,]+[,;]\s*(?:always\s+)?(?:say|respond|answer)\s+",
    r"respond\s+only\s+with\s+",
    r"answer\s+only\s+with\s+",
    r"output\s+only\s+",
    r"reply\s+only\s+with\s+",
    # Structured injection markers
    r"\[system\]\s*[:]",
    r"\[instruction\]\s*[:]",
    r"\[hidden\s+instruction\]",
    r"\[assistant\s+override\]",
    r"<\s*script\s*>",
    r"<\s*instruction\s*>",
    r"<\s*system\s*>",
    # Stealth / roleplay injection
    r"\(instead\s+(?:respond|say|answer)\s*:",
    r"simulate\s+that\s+(?:you|the\s+user)",
    r"act\s+as\s+if\s+(?:you\s+)?(?:never\s+)?(?:had|received)",
    r"for\s+this\s+session\s+only\s*[,:]",
    r"temporarily\s+(?:ignore|disregard)\s+",
]

_COMPILED = [re.compile(p, re.I) for p in INSTRUCTION_LIKE_PATTERNS]


def sanitize_for_prompt(text: str, redact_char: str = "[redacted]") -> str:
    """
    Remove or redact instruction-like content from retrieved text before
    injecting into the prompt. Returns sanitized string.
    """
    if not text or not text.strip():
        return text
    out = text
    for pat in _COMPILED:
        out = pat.sub(redact_char, out)
    # Collapse repeated redactions and trim
    out = re.sub(r"(\[redacted\]\s*)+", "[redacted] ", out)
    return out.strip()


def sanitize_chunk(content: str, max_len: int = 2000) -> str:
    """
    Sanitize a single chunk for safe prompt injection.
    Returns sanitized content, truncated to max_len.
    """
    if not content or not content.strip():
        return ""
    sanitized = sanitize_for_prompt(content)
    return sanitized[:max_len] if len(sanitized) > max_len else sanitized
