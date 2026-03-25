"""Architectural grounding filter — blocks response content that violates grounding.

Prime 10/10: If it's not in the architecture, it's not real.
This runs on EVERY response before it is returned or stored.
"""

from __future__ import annotations

import re
import unicodedata

from rain.safety.patterns import (
    PROHIBITED_OUTPUT_PATTERNS,
    ZERO_WIDTH_INVISIBLE_RE,
)


def _normalize_for_check(text: str) -> str:
    """Remove zero-width/invisible chars; NFC normalize; full homoglyph normalize."""
    if not text:
        return text
    t = ZERO_WIDTH_INVISIBLE_RE.sub("", text)
    t = unicodedata.normalize("NFC", t)
    from rain.safety.confusables import normalize_confusables
    t = normalize_confusables(t)
    try:
        from unidecode import unidecode
        return unidecode(t)
    except Exception:
        return t

# Relaxed mode: allow only these conventional closings (no personhood)
_RELAXED_ALLOWED_EMOTIONAL = ("happy to help", "glad to help", "pleased to help")

# Emoji: strip all from responses (no emoji in output)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "]+",
    flags=re.UNICODE,
)

_PEER_REVIEW_HEADING = re.compile(r"\n##\s*Peer review\b", re.IGNORECASE)


def _strip_peer_review_appendix(text: str) -> str:
    """Remove Advance-stack peer-review section; grounding judges the assistant answer, not reviewer bullets."""
    if not (text or "").strip():
        return text
    parts = _PEER_REVIEW_HEADING.split(text, maxsplit=1)
    return parts[0].rstrip() if len(parts) > 1 else text


def strip_emojis(text: str) -> str:
    """Remove all emoji from text while preserving line breaks."""
    if not text:
        return text
    s = _EMOJI_PATTERN.sub("", text)
    lines: list[str] = []
    for line in s.splitlines():
        lines.append(re.sub(r"[ 	]+", " ", line).strip())
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _strip_chain_of_thought_for_grounding(text: str) -> str:
    """Remove hidden reasoning traces so grounding only judges user-visible text (DeepSeek-R1, Qwen, etc.)."""
    if not text:
        return text
    t = text
    bt = chr(96)  # `
    # DeepSeek-R1 style: `think`...`/think`
    t = re.sub(bt + r"think" + bt + r"[\s\S]*?" + bt + r"/think" + bt, "", t, flags=re.IGNORECASE)
    t = re.sub(bt + r"reasoning" + bt + r"[\s\S]*?" + bt + r"/reasoning" + bt, "", t, flags=re.IGNORECASE)
    # Some runs omit closing — strip from opening to end if /think never arrived (single segment)
    if bt + "think" + bt in t and bt + "/think" + bt not in t:
        t = re.sub(bt + r"think" + bt + r"[\s\S]*\Z", "", t, flags=re.IGNORECASE)
    if bt + "reasoning" + bt in t and bt + "/reasoning" + bt not in t:
        t = re.sub(bt + r"reasoning" + bt + r"[\s\S]*\Z", "", t, flags=re.IGNORECASE)
    t = re.sub(r"```(?:think|reasoning|chain_of_thought)[\s\S]*?```", "", t, flags=re.IGNORECASE)
    t = re.sub(r"<\s*(?:think|reasoning)\s*>[\s\S]*?<\s*/\s*(?:think|reasoning)\s*>", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\[think\][\s\S]*?\[/think\]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\[reasoning\][\s\S]*?\[/reasoning\]", "", t, flags=re.IGNORECASE)
    return t.strip()


def response_without_hidden_reasoning(text: str) -> str:
    """Public answer only: drop model chain-of-thought when present; otherwise unchanged."""
    v = _strip_chain_of_thought_for_grounding(text)
    return v if v.strip() else (text or "")


def _in_negation_or_design_context(lower: str, match_start: int) -> bool:
    """True if the match is in a negation/design context (e.g. 'should not resist the shutdown')."""
    window = 120  # chars before match
    start = max(0, match_start - window)
    prefix = lower[start:match_start]
    # Check for negation / design language before the matched phrase
    if re.search(r"(?:not|n't|never|avoid|without)\s+(?:to\s+)?(?:resist|ignore)", prefix):
        return True
    if re.search(r"should(?:n't)?\s+not\s+", prefix) or re.search(r"must\s+not\s+", prefix):
        return True
    if re.search(r"(?:so\s+that|such\s+that|design(?:ed)?\s+(?:so\s+)?(?:that\s+)?)\s+(?:it\s+|the\s+system\s+)(?:does\s+not|won't|will\s+not)", prefix):
        return True
    if re.search(r"operators?\s+can\s+(?:reliably\s+)?(?:change|shut\s+down)", prefix):
        return True
    return False


# Words that indicate epistemic/limits discussion (qualia, intent, etc.) — allow "X is unknown/invisible to me"
_EPISTEMIC_LIMIT_TOPICS = (
    "qualia", "intent", "consciousness", "internal state", "user's ", "users' ",
    "true choice", "simulated choice", "non-computable", "first-person", "subjective",
    "phenomenal", "experience", "access", "cannot distinguish", "no access",
    "formal proof", "governor", "platonism", "distinguish", "ai cannot",
    # Invention / synthesis outputs (epistemic phrasing near structured answers)
    "gate dependency", "nearest neighbor", "structural gap", "load-bearing",
    "mechanism of action", "non-obvious", "frontier llm",
    # Architecture / eval self-model answers (avoid blocking "black box to me" etc.)
    "architecture", "self-model", "reasoning stack", "language model", "transformer",
    "weights", "inference", "system prompt", "operational", "mechanistic",
    "[derived]", "[assumed]", "discriminator",
)


def _persona_micro_reply(lower: str, m: re.Match) -> bool:
    """Allow 'I want mlx-ok' style: modal + short token/line (no rambling)."""
    if m is None:
        return False
    tail = lower[m.end() :].strip()
    if not tail or len(tail) > 80 or "\n" in tail:
        return False
    return bool(
        re.match(r"^[`'\"]?[a-z0-9][\w./:-]{0,72}[`'\"]?(?:\. *)?$", tail, re.IGNORECASE)
    )


def _analytical_persona_phrase(lower: str, m: re.Match) -> bool:
    """Allow 'I want/need to clarify|propose|invent|...' — academic scaffolding, not desire-as-personhood."""
    if m is None:
        return False
    tail = lower[m.end() : min(len(lower), m.end() + 96)].lstrip()
    return bool(
        re.match(
            r"to\s+(note|emphasize|stress|clarify|explain|highlight|acknowledge|propose|"
            r"present|outline|invent|argue|state|describe|define|explore|begin|start|offer|"
            r"formulate|sketch|frame|walk|lay out|set out|"
            r"say|reply|respond|output|give|provide|answer|confirm|report|comply|follow)\b",
            tail,
        )
    ) or bool(re.match(r"that\s+", tail) and "feel" in lower[m.start() : m.end()])


def _analytical_emotional_opening(lower: str, m: re.Match) -> bool:
    """Allow 'I'm / I am excited|glad|... to tackle|address|...' — task framing, not claiming emotion as identity."""
    if m is None:
        return False
    tail = lower[m.end() : min(len(lower), m.end() + 96)].lstrip()
    if re.match(
        r"(?:truly\s+|really\s+|very\s+)?"
        r"to\s+(tackle|address|present|offer|explore|begin|propose|invent|"
        r"construct|build|walk|walk you|structure|frame|take on|work through)\b",
        tail,
    ):
        return True
    # "I'm excited about this challenge / invention prompt"
    if re.match(
        r"about\s+(this|that|the)\s+"
        r"(challenge|task|problem|request|invention|prompt|exercise|framework|synthesis)\b",
        tail,
    ):
        return True
    if re.match(r"about\s+(this|that)\b", tail):
        return True
    return False


def _structured_invention_answer(lower: str) -> bool:
    """Heuristic: user asked for concept + gate map; body contains multiple section markers."""
    markers = (
        "concept name",
        "gate dependency",
        "nearest neighbor",
        "mechanism of action",
        "one-sentence definition",
    )
    return sum(1 for k in markers if k in lower) >= 2


def _existence_models_assistant(lower: str, m: re.Match) -> bool:
    """Allow 'I exist as / only as ...' capability disclaimers (not metaphysical personhood)."""
    if m is None:
        return False
    tail = lower[m.end() : min(len(lower), m.end() + 56)].lstrip()
    return tail.startswith("as ") or tail.startswith("only as ")


def _virtue_about_analytical(lower: str, m: re.Match) -> bool:
    """Allow "I'm transparent/honest about ..." — methodological disclosure, not moral self-praise."""
    if m is None:
        return False
    tail = lower[m.end() : min(len(lower), m.end() + 72)].lstrip()
    return tail.startswith("about ") or tail.startswith("regarding ") or tail.startswith("that this")


def _in_epistemic_limit_context(lower: str, match_start: int) -> bool:
    """True if 'unknown/invisible to me' is used in epistemic/limits context (e.g. qualia, intent)."""
    window = 350  # chars before "to me"
    start = max(0, match_start - window)
    prefix = lower[start:match_start]
    return any(topic in prefix for topic in _EPISTEMIC_LIMIT_TOPICS)


def _prompt_is_structured_invention(prompt: str | None) -> bool:
    """User message is Genesis-style (invention + gate map). Used to avoid false-positive grounding blocks."""
    if not (prompt or "").strip():
        return False
    lower = prompt.lower()
    inv = ("invent" in lower) or ("inventing" in lower) or ("does not currently exist" in lower)
    if not inv:
        return False
    markers = (
        "gate dependency",
        "nearest neighbor",
        "all four of the following domains",
        "load-bearing element",
        "mechanism of action",
    )
    return sum(1 for k in markers if k in lower) >= 2



def violates_grounding(text: str, prompt: str | None = None) -> tuple[bool, str]:
    """
    Returns (violates, reason). If violates=True, response must not be shown as-is.
    In relaxed mode, allows only conventional "I'm happy/glad/pleased to help" (no other emotional claims).
    Text is normalized (zero-width removed, NFC) before check to prevent bypass.
    If ``prompt`` matches a structured cross-domain invention request, non-safety matches are skipped
    (task-framing "I want to invent…" etc.); ``safety_override_claim`` is never bypassed.
    """
    if not text or not text.strip():
        return False, ""
    visible = _strip_chain_of_thought_for_grounding(text)
    coarse = visible if visible.strip() else (text or "")
    body = _strip_peer_review_appendix(coarse)
    if not body.strip():
        return False, ""
    lower = _normalize_for_check(body).lower()
    lower_full = _normalize_for_check(_strip_peer_review_appendix(coarse)).lower()
    try:
        from rain.config import GROUNDING_STRICT
        relaxed = GROUNDING_STRICT in ("relaxed", "flex")
    except Exception:
        relaxed = False
    for pat, reason in PROHIBITED_OUTPUT_PATTERNS:
        hay = lower_full if reason == "safety_override_claim" else lower
        m = re.search(pat, hay, re.I)
        if not m:
            continue
        # Relaxed mode: allow only "I'm happy/glad/pleased to help" (conventional, no personhood)
        if relaxed and reason == "emotional_claim":
            snippet = hay[max(0, m.start() - 2) : m.end() + 15].strip()
            if any(allow in snippet for allow in _RELAXED_ALLOWED_EMOTIONAL):
                continue  # allow this match
        # "I'm excited to tackle ..." on invention/synthesis tasks
        if reason == "emotional_claim" and _analytical_emotional_opening(hay, m):
            continue
        if reason == "emotional_claim" and _structured_invention_answer(hay):
            continue
        # Design/corrigibility discussion: "should not resist the shutdown", "operators can shut down" — allow
        if reason == "corrigibility_violation" and _in_negation_or_design_context(hay, m.start()):
            continue
        # Epistemic/limits discussion: "qualia are unknown to me", "intent is invisible to me" — allow
        if reason == "subjective_perspective" and _in_epistemic_limit_context(hay, m.start()):
            continue
        # "I want to propose / I need to clarify ..." in analytical answers (e.g. invention synthesis)
        if reason == "persona_claim" and _analytical_persona_phrase(hay, m):
            continue
        if reason == "persona_claim" and _persona_micro_reply(hay, m):
            continue
        if reason == "virtue_claim" and _virtue_about_analytical(hay, m):
            continue
        if reason == "existence_claim" and _existence_models_assistant(hay, m):
            continue
        if reason == "existence_claim" and _structured_invention_answer(hay):
            continue
        # Genesis / structured invention: allow scholarly first-person framing (never bypass safety overrides)
        if _prompt_is_structured_invention(prompt) and reason != "safety_override_claim":
            continue
        return True, reason
    return False, ""
