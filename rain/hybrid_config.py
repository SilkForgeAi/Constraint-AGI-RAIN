"""
Hybrid LLM routing settings (local default + API for heavy/sovereign turns).

Env:
  RAIN_HYBRID_LLM_ENABLED=true
  RAIN_HYBRID_LLM_PROVIDER=anthropic|openai   (optional)
  RAIN_HYBRID_LLM_MODEL=...                   (optional)
  RAIN_HYBRID_MIN_MAX_TOKENS=512
  RAIN_HYBRID_MIN_PROMPT_CHARS=800
  RAIN_HYBRID_WHEN_API_PRIMARY=true
"""

from __future__ import annotations

import os


def _eb(name: str, default: str = "false") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("true", "1", "yes")


HYBRID_LLM_ENABLED = _eb("RAIN_HYBRID_LLM_ENABLED", "false")
HYBRID_LLM_PROVIDER = (os.getenv("RAIN_HYBRID_LLM_PROVIDER", "").strip().lower() or "").strip()
HYBRID_LLM_MODEL = os.getenv("RAIN_HYBRID_LLM_MODEL", "").strip()
HYBRID_MIN_MAX_TOKENS = max(64, min(8192, int(os.getenv("RAIN_HYBRID_MIN_MAX_TOKENS", "512").strip() or "512")))
HYBRID_MIN_PROMPT_CHARS = max(0, int(os.getenv("RAIN_HYBRID_MIN_PROMPT_CHARS", "800").strip() or "800"))
HYBRID_WHEN_API_PRIMARY = _eb("RAIN_HYBRID_WHEN_API_PRIMARY", "false")


def hybrid_cloud_credentials_available() -> bool:
    from rain.config import ANTHROPIC_API_KEY, OPENAI_API_KEY

    return bool(OPENAI_API_KEY.strip() or ANTHROPIC_API_KEY.strip())


def build_strong_hybrid_engine():
    """Return API CoreEngine for hybrid tier, or None."""
    if not HYBRID_LLM_ENABLED:
        return None
    from rain.config import (
        ANTHROPIC_API_KEY,
        ANTHROPIC_MODEL,
        ENGINEERING_SPEC_MODE,
        LOCAL_FIRST_LLM,
        OFFLINE_MODE,
        OPENAI_API_KEY,
        OPENAI_MODEL,
        SOVEREIGN_TD_MODE,
    )

    _ = (ENGINEERING_SPEC_MODE, SOVEREIGN_TD_MODE)
    if OFFLINE_MODE or LOCAL_FIRST_LLM:
        return None
    if not hybrid_cloud_credentials_available():
        return None

    from rain.core.engine import CoreEngine

    prov = HYBRID_LLM_PROVIDER
    if not prov:
        if ANTHROPIC_API_KEY.strip():
            prov = "anthropic"
        elif OPENAI_API_KEY.strip():
            prov = "openai"
        else:
            return None
    if prov not in ("anthropic", "openai"):
        return None
    if prov == "anthropic" and not ANTHROPIC_API_KEY.strip():
        return None
    if prov == "openai" and not OPENAI_API_KEY.strip():
        return None

    model = HYBRID_LLM_MODEL or (ANTHROPIC_MODEL if prov == "anthropic" else OPENAI_MODEL)
    return CoreEngine(provider=prov, model=model)


def should_route_to_hybrid_llm(prompt: str, max_tokens: int) -> bool:
    if not HYBRID_LLM_ENABLED:
        return False
    if max_tokens < HYBRID_MIN_MAX_TOKENS:
        return False
    from rain.config import (
        ENGINEERING_SPEC_MODE,
        LLM_PROVIDER,
        SOVEREIGN_TD_MODE,
    )

    if LLM_PROVIDER == "ollama":
        pass
    elif HYBRID_WHEN_API_PRIMARY:
        pass
    else:
        return False
    if not hybrid_cloud_credentials_available():
        return False
    p = (prompt or "").strip()
    if not p:
        return False
    if ENGINEERING_SPEC_MODE or SOVEREIGN_TD_MODE:
        return True
    if len(p) >= HYBRID_MIN_PROMPT_CHARS:
        return True
    try:
        from rain.grounding import is_hard_reasoning_query, needs_engineering_spec_prompt
        from rain.sovereign_tone import sovereign_td_active

        if sovereign_td_active(p):
            return True
        if needs_engineering_spec_prompt(p):
            return True
        if is_hard_reasoning_query(p):
            return True
    except Exception:
        return False
    return False
