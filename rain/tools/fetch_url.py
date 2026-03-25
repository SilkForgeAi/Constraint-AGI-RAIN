"""Fetch URL tool — allowlist-only, read-only, size-limited. Gated by RAIN_FETCH_URL_ENABLED and RAIN_FETCH_URL_ALLOWLIST."""

from __future__ import annotations

MAX_FETCH_BYTES = 500 * 1024  # 500 KB


def _url_allowed(url: str, allowlist: list[str]) -> bool:
    """True if url is allowed (must match an allowlist prefix)."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False
    for prefix in allowlist:
        p = prefix.strip().lower()
        if not p.startswith(("http://", "https://")):
            p = "https://" + p
        if url.lower().startswith(p) or p.endswith("/") and url.lower().startswith(p.rstrip("/")):
            return True
    return False


def fetch_url(url: str) -> str:
    """
    Fetch URL content (read-only). Only URLs whose prefix is in RAIN_FETCH_URL_ALLOWLIST are allowed.
    Max 500KB. No code execution; text only.
    """
    from rain.config import FETCH_URL_ALLOWLIST, FETCH_URL_ENABLED, OUTBOUND_NETWORK_ALLOWED

    if not OUTBOUND_NETWORK_ALLOWED:
        return (
            "URL fetch is disabled (RAIN_OFFLINE_MODE=true or RAIN_ALLOW_OUTBOUND=false). "
            "Use read_file on local paths or RAG when offline."
        )

    if not FETCH_URL_ENABLED:
        return "URL fetch is disabled. Set RAIN_FETCH_URL_ENABLED=true and RAIN_FETCH_URL_ALLOWLIST=... to enable."

    if not FETCH_URL_ALLOWLIST:
        return "URL fetch has no allowlist. Set RAIN_FETCH_URL_ALLOWLIST (comma-separated URLs or domains)."

    if not url or not url.strip():
        return "Error: No URL provided."

    url = url.strip()
    if not _url_allowed(url, FETCH_URL_ALLOWLIST):
        return "Error: URL not on allowlist."

    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Rain/1.0 (allowlist fetch)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read(MAX_FETCH_BYTES)
        if len(content) >= MAX_FETCH_BYTES:
            content = content + b"\n\n[Truncated: response exceeds 500KB.]"
        return content.decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error: {str(e)[:200]}"
