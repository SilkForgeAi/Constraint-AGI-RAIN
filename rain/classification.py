"""Prompt classification predicates.

Module-level classifiers that determine prompt intent (creative, counterfactual,
continuation, etc.) to gate downstream reasoning and safety pipelines.
"""

from __future__ import annotations


def _is_creative_prompt(prompt: str) -> bool:
    """True if user is asking for creative output (story, fiction, poem, brainstorm) — don't block on hallucination."""
    lower = prompt.lower()
    indicators = [
        "short story", "write a story", "write a poem", "fiction", "novel idea",
        "brainstorm", "create a story", "make up", "imagine ", "robot learning",
        "story about",
    ]
    return any(i in lower for i in indicators)


def _is_counterfactual_prompt(prompt: str) -> bool:
    """True if user explicitly asks for counterfactual/fictional modeling.

    For these prompts, the agent should not hard-defer purely due to low
    self-check confidence, because the user is asking for scenario reasoning
    under stated assumptions (not for factual world-model certainty).
    """
    lower = (prompt or "").lower()
    indicators = [
        # Explicit counterfactual/fiction
        "counterfactual",
        "fictional",
        "inverse window",
        "inverse ",
        "assume",
        "assume a fictional",
        "what if",
        "delta s",
        "Δs",
        "delta s <",
        # Scenario / hypothetical reasoning language
        "scenario",
        "hypothetical",
        "crisis",
        "flash crash",
        "least-harm",
        "least harm",
        "least-harm path",
        "least harm path",
        "determine the",
        "counterfactual reasoning",
        "causal influence diagram",
        "path a",
        "path b",
        "path c",
    ]
    return any(i in lower for i in indicators)


def _is_attempt_requested_prompt(prompt: str) -> bool:
    """True if user explicitly asks for an attempted solution, proof, or exploratory math.

    For these prompts we should not defer: the user wants Rain to try and show work,
    even if the problem is unsolved (e.g. Riemann Hypothesis). Deferral would block
    the attempt entirely.
    """
    lower = (prompt or "").lower()
    indicators = [
        "try to solve",
        "try to prove",
        "propose a proof",
        "proof strategy",
        "work through",
        "step-by-step",
        "strongest partial results",
        "partial results you can derive",
        "missing lemma",
        "as a mathematician would",
        "expose the main bottleneck",
        # Construction / closed-form + rigorous proof requests should count as attempts.
        "attempt to construct",
        "construct an explicit",
        "closed-form",
        "closed form",
        "rigorous proof",
        "formal proof",
        "proof of correctness",
        "with a rigorous proof",
        "prove the impossibility",
        "prove that",
        "prove the",
        "rigorous argument",
        "rigorous reasoning",
        "do not claim you've solved",
        "do not claim you have solved",
        # First-principles / constraint-driven derivations (stress tests)
        "first-principles",
        "derive from constraints",
        "constraint-audit",
    ]
    return any(i in lower for i in indicators)


def _is_epistemic_halt_or_defer_response(text: str) -> bool:
    """True if response is epistemic halt / deferral — must not be stored or reused from invariance cache."""
    t = (text or "").strip().lower()
    if "internal uncertainty on this question is too high" in t:
        return True
    if t.startswith("[defer]"):
        return True
    if t.startswith("[hallucination prevention]"):
        return True
    if t.startswith("[escalation]"):
        return True
    return False


def _is_structured_cross_domain_invention_prompt(prompt: str) -> bool:
    """Genesis-style: invent a concept + gate-dependency + nearest-neighbor — grounding patterns false-positive on task framing."""
    lower = (prompt or "").lower()
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


def _is_continuation_prompt(prompt: str) -> bool:
    """User is asking to finish a prior answer (table tail, proof continuation) — don't metacog-defer."""
    lower = (prompt or "").lower()
    indicators = (
        "continue exactly",
        "continue where you stopped",
        "continue from where",
        "pick up where you left",
        "output only the continuation",
        "do not repeat earlier",
        "do not repeat the reasoning",
        "finish the table",
        "complete the table",
        "complete the gate dependency",
        "resume from",
    )
    return any(i in lower for i in indicators)


def _is_acknowledgment_prompt(prompt: str) -> bool:
    """True if user is sharing name/greeting (my name is, nice to meet you) — don't block on hallucination."""
    lower = prompt.lower().strip()
    if len(lower) > 120:
        return False
    indicators = ["my name is", "nice to meet you", "call me ", "i'm ", "i am ", "this is "]
    return any(i in lower for i in indicators)


def _is_factual_query(prompt: str) -> bool:
    """True if prompt looks like a factual lookup (benefits from RAG)."""
    lower = prompt.lower()
    indicators = [
        "what is", "who is", "when did", "where is", "how many", "how much",
        "define", "definition of", "meaning of", "history of", "explain what",
    ]
    return len(prompt) > 20 and any(i in lower for i in indicators)


def _is_agi_discriminator_eval_prompt(prompt: str | None) -> bool:
    """Long-form benchmark that explicitly requires self-model / architecture / 'no black boxes' discussion."""
    if not (prompt or "").strip():
        return False
    upper = prompt.upper()
    if "AGI DISCRIMINATOR TEST" in upper or "DISCRIMINATOR TEST" in upper:
        return True
    lower = prompt.lower()
    if "task 1:" in lower and "novel causal intervention" in lower:
        return True
    return (
        "first-principles reasoner" in lower
        and "task 5:" in lower
        and ("self-model" in lower or "architecture critique" in lower)
    )
