"""Health check for Rain: config and env validation. No secrets logged."""
from __future__ import annotations
import os

def health_check() -> tuple[bool, str]:
    """Returns (ok, message). Never logs secrets."""
    from rain.config import DATA_DIR, LOCAL_FIRST_LLM, OFFLINE_MODE, OUTBOUND_NETWORK_ALLOWED, LLM_PROVIDER
    issues = []
    if LOCAL_FIRST_LLM:
        issues.append("RAIN_LOCAL_FIRST_LLM (Ollama only)")
    if OFFLINE_MODE:
        issues.append("RAIN_OFFLINE_MODE (no outbound tools)")
    if not OUTBOUND_NETWORK_ALLOWED and not OFFLINE_MODE:
        issues.append("RAIN_ALLOW_OUTBOUND=false")
    issues.append(f"LLM_PROVIDER={LLM_PROVIDER}")
    ak = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    ok_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if ak:
        issues.append("ANTHROPIC_API_KEY set")
    if ok_key:
        issues.append("OPENAI_API_KEY set")
    use_ollama = LLM_PROVIDER == "ollama" or LOCAL_FIRST_LLM or OFFLINE_MODE
    if use_ollama or (not ak and not ok_key):
        try:
            import urllib.request
            base = os.environ.get("RAIN_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/").replace("/v1", "")
            urllib.request.urlopen(base + "/api/tags", timeout=2)
            issues.append("Ollama reachable")
        except Exception:
            if use_ollama:
                return False, "Local-first/offline: Ollama not reachable (start Ollama or fix RAIN_OLLAMA_BASE_URL)"
            if not ak and not ok_key:
                return False, "No LLM: set ANTHROPIC_API_KEY or OPENAI_API_KEY, or run Ollama"
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"DATA_DIR not writable: {e}"
    if not issues:
        return False, "Config check failed: no backend"
    return True, "OK: " + "; ".join(issues)
