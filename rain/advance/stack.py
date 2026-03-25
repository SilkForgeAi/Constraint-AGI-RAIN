"""
Advance Stack — unified, opt-in layer that only *adds* behavior (no silent regressions).

Enable with RAIN_ADVANCE_STACK=1. Optional: draft vs strong model routing, peer review, JSONL audit.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _events_path() -> Path:
    from rain.config import DATA_DIR

    p = DATA_DIR / "logs" / "advance_events.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def log_event(event: dict[str, Any]) -> None:
    """Append one JSON line for calibration / ops (never raises)."""
    try:
        e = dict(event)
        e.setdefault("ts", datetime.now(timezone.utc).isoformat())
        path = _events_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _routing_complexity_score(prompt: str) -> int:
    """Higher score → prefer strong model (draft/strong routing)."""
    p = (prompt or "").strip()
    low = p.lower()
    score = 0
    if len(p) > 400:
        score += 1
    if len(p) > 2000:
        score += 2
    if len(p) > 8000:
        score += 3
    if p.count("\n") > 8:
        score += 1
    if p.count("\n") > 20:
        score += 2
    heavy = (
        "prove ", "proof ", "theorem", "lemma", "design a system", "architecture",
        "adversarial", "red-team", "constraint", "first-principles", "derive ",
        "implement", "python", "formal", "investment", "legal", "medical",
        "diagnos", "contract", "security", "cryptograph", "kernel",
    )
    for h in heavy:
        if h in low:
            score += 2
    if any(x in low for x in ("attempt", "step-by-step", "falsification", "constraint-audit")):
        score += 2
    return score


def _use_strong_model_for_routing(prompt: str) -> bool:
    """True → use strong model when draft/strong pair is configured."""
    return _routing_complexity_score(prompt) >= 3


def begin_routing(engine: Any, prompt: str) -> str | None:
    """If routing is configured, set engine.model; return previous model name for restore."""
    try:
        from rain.config import (
            ADVANCE_DRAFT_MODEL,
            ADVANCE_STACK_ENABLED,
            ADVANCE_STRONG_MODEL,
        )
    except Exception:
        return None
    if not ADVANCE_STACK_ENABLED:
        return None
    if not ADVANCE_DRAFT_MODEL or not ADVANCE_STRONG_MODEL:
        return None
    old = getattr(engine, "model", None)
    strong = _use_strong_model_for_routing(prompt)
    engine.model = ADVANCE_STRONG_MODEL if strong else ADVANCE_DRAFT_MODEL
    log_event(
        {
            "kind": "advance_routing",
            "selected": engine.model,
            "routing_complexity": _routing_complexity_score(prompt),
            "strong": strong,
        }
    )
    return old


def end_routing(engine: Any, previous_model: str | None) -> None:
    if previous_model is not None:
        engine.model = previous_model


@contextmanager
def routing_context(engine: Any, prompt: str):
    """Ensures model restore on any exit path (including early return)."""
    prev = begin_routing(engine, prompt)
    try:
        yield
    finally:
        end_routing(engine, prev)


def extra_system_instructions(prompt: str) -> str:
    """Extra system text when RAIN_ADVANCE_STACK=1 (additive only)."""
    try:
        from rain.config import ADVANCE_STACK_ENABLED, ADVANCE_UNCERTAINTY_PROMPT
    except Exception:
        return ""
    if not ADVANCE_STACK_ENABLED:
        return ""
    if not ADVANCE_UNCERTAINTY_PROMPT:
        return ""
    return (
        "\n\n[Advance stack — epistemic discipline]\n"
        "- Tag non-obvious factual claims with [ASSUMED] or [DERIVED] where applicable.\n"
        "- State at least one **falsification** or **what would change my mind** for non-trivial conclusions.\n"
        "- List **top unknowns** when the problem is under-specified.\n"
        "- Do not claim to have executed code or accessed systems unless tool results say so.\n"
    )


def _should_run_peer_review(
    mode: str,
    prompt: str,
    response: str,
    verification_ran: bool | None,
    verification_ok: bool | None,
) -> bool:
    """Decide whether to spend an extra review call (cost control)."""
    if mode == "off":
        return False
    if mode == "always":
        return True
    if mode == "verify_fail":
        return bool(verification_ran and verification_ok is False)
    if mode == "critical":
        try:
            from rain.reasoning.verify import is_critical_prompt
        except Exception:
            def is_critical_prompt(_p: str) -> bool:  # noqa: E306
                return False
        if is_critical_prompt(prompt):
            return True
        if len(response or "") > 12_000 or len(prompt or "") > 6000:
            return True
        low = (prompt or "").lower()
        if any(x in low for x in ("first-principles", "constraint-audit", "adversarial", "red-team", "prove ", "theorem")):
            return True
        return _routing_complexity_score(prompt) >= 6
    return False


def maybe_peer_review_append(
    engine: Any,
    prompt: str,
    response: str,
    *,
    verification_ran: bool | None = None,
    verification_ok: bool | None = None,
) -> str:
    """
    Optional second pass: strong model lists gaps (does not rewrite full answer).
    Policy: RAIN_ADVANCE_PEER_REVIEW_MODE = off | always | critical | verify_fail.
    """
    try:
        from rain.config import (
            ADVANCE_PEER_REVIEW_MODE,
            ADVANCE_STACK_ENABLED,
            ADVANCE_STRONG_MODEL,
            SPEED_PRIORITY,
        )
    except Exception:
        return response
    if not ADVANCE_STACK_ENABLED or SPEED_PRIORITY:
        return response
    if ADVANCE_PEER_REVIEW_MODE == "off":
        return response
    if not _should_run_peer_review(
        ADVANCE_PEER_REVIEW_MODE, prompt, response, verification_ran, verification_ok
    ):
        return response
    if not (response or "").strip() or len(response) > 120_000:
        return response
    review_model = ADVANCE_STRONG_MODEL
    if not review_model:
        return response
    prev = getattr(engine, "model", None)
    engine.model = review_model
    try:
        rev_msgs = [
            {
                "role": "user",
                "content": (
                    "You are a critical reviewer. Read the USER TASK and the ASSISTANT ANSWER.\n"
                    "Output a short markdown section titled ## Peer review (max 12 bullet points):\n"
                    "- Gaps, missing checks, or overstated confidence\n"
                    "- What a human should verify independently\n"
                    "Do NOT rewrite the full answer. Be concise.\n\n"
                    f"USER TASK (excerpt):\n{(prompt or '')[:4000]}\n\n"
                    f"ASSISTANT ANSWER (excerpt):\n{(response or '')[:8000]}"
                ),
            }
        ]
        note = engine.complete(rev_msgs, temperature=0.2, max_tokens=1024).strip()
        if note:
            log_event(
                {
                    "kind": "advance_peer_review",
                    "len": len(note),
                    "mode": ADVANCE_PEER_REVIEW_MODE,
                }
            )
            return (response.rstrip() + "\n\n" + note).strip()
    except Exception as e:
        log_event({"kind": "advance_peer_review_error", "error": str(e)[:200]})
    finally:
        if prev is not None:
            engine.model = prev
    return response


def log_verification_result(ok: bool | None, prompt_preview: str, note: str | None = None) -> None:
    """Append verification outcome for calibration dashboards."""
    log_event(
        {
            "kind": "verification",
            "ok": ok,
            "note": (note or "")[:300],
            "prompt_preview": prompt_preview[:200],
        }
    )
