"""Web search — optional, gated. Uses DuckDuckGo when available. 15s timeout."""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*renamed.*", category=RuntimeWarning)

SEARCH_TIMEOUT = 15


def web_search(query: str, max_results: int = 5, timeout_sec: int = SEARCH_TIMEOUT) -> str:
    """
    Search the web. Returns formatted results or error.
    Requires: pip install duckduckgo-search
    """
    try:
        from rain.config import OUTBOUND_NETWORK_ALLOWED
        if not OUTBOUND_NETWORK_ALLOWED:
            return (
                "Web search is disabled (RAIN_OFFLINE_MODE=true or RAIN_ALLOW_OUTBOUND=false). "
                "Use query_rag / local documents, or re-enable outbound when online."
            )
    except Exception:
        pass
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS
        except ImportError:
            return "Web search not available. Install: pip install duckduckgo-search"

    if not query or len(query.strip()) < 3:
        return "Query too short."
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            def _do_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            fut = ex.submit(_do_search)
            results = fut.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        return "Search timed out."
    except Exception as e:
        return f"Search error: {str(e)[:100]}"
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results[:max_results], 1):
        title = r.get("title", "?")
        url = r.get("href", "")
        snippet = r.get("body", "")[:200]
        lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    return "\n\n".join(lines)
