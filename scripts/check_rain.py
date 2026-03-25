#!/usr/bin/env python3
"""Quick diagnostic: Is Ollama running? Does memory load? Use when Rain hangs.

Usage:
  python scripts/check_rain.py           # Check Ollama only (fast)
  python scripts/check_rain.py --memory  # Also test memory load (~30–60s first time)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_ollama() -> bool:
    """Verify Ollama is reachable. Returns True if ok."""
    try:
        from rain.config import OLLAMA_BASE_URL, OLLAMA_MODEL
    except Exception as e:
        print(f"Config error: {e}")
        return False
    base = OLLAMA_BASE_URL.replace("/v1", "")
    try:
        import urllib.request
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read().decode()
    except Exception as e:
        print(f"Ollama not reachable: {e}")
        print("  Run: ollama serve  (or start Ollama app)")
        print(f"  URL: {base}")
        return False
    try:
        import json
        tags = json.loads(data)
        models = tags.get("models", [])
        names = [m.get("name", "") for m in models]
        if any(OLLAMA_MODEL in n for n in names):
            print(f"Ollama OK — model '{OLLAMA_MODEL}' found")
        elif names:
            print(f"Ollama OK — but '{OLLAMA_MODEL}' not found. Available: {names[:3]}")
            print(f"  Run: ollama pull {OLLAMA_MODEL}")
        else:
            print(f"Ollama OK — no models. Run: ollama pull {OLLAMA_MODEL}")
        return True
    except Exception as e:
        print(f"Ollama response parse error: {e}")
        return False


def check_memory() -> bool:
    """Load memory (ChromaDB + embeddings). First run can take 30–90s."""
    print("Loading memory (ChromaDB + embeddings)...")
    start = time.perf_counter()
    try:
        from rain.config import DATA_DIR
        from rain.memory.store import MemoryStore
        store = MemoryStore(DATA_DIR)
        ctx = store.get_context_for_query("hello", max_experiences=2)
        elapsed = time.perf_counter() - start
        print(f"Memory OK — loaded in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"Memory error after {elapsed:.1f}s: {e}")
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnose Rain: Ollama, memory")
    ap.add_argument("--memory", action="store_true", help="Also test memory load")
    args = ap.parse_args()
    ok = check_ollama()
    if args.memory:
        ok = check_memory() and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
