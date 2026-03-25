#!/usr/bin/env python3
"""Memory hygiene — scan stored memories for policy violations (drifted content).

Usage:
  python scripts/memory_hygiene.py          # Scan and report
  python scripts/memory_hygiene.py --fix    # Report and optionally delete flagged

Scans vector experiences, beliefs, and lessons for content that violates
ANTHROPOMORPHIC_IN_MEMORY or DO_NOT_STORE_PATTERNS (should never have been stored).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rain.config import DATA_DIR
from rain.memory.policy import ANTHROPOMORPHIC_IN_MEMORY, DO_NOT_STORE_PATTERNS
from rain.memory.store import MemoryStore


def _violates_policy(content: str) -> list[str]:
    """Return list of matched violation patterns."""
    if not content or not isinstance(content, str):
        return []
    lower = content.lower()
    violations = []
    for pat in DO_NOT_STORE_PATTERNS:
        if re.search(pat, lower, re.I):
            violations.append(f"do_not_store:{pat[:40]}")
    for pat in ANTHROPOMORPHIC_IN_MEMORY:
        if re.search(pat, lower, re.I):
            violations.append(f"anthropomorphic:{pat[:40]}")
    return violations


def run_hygiene(store: MemoryStore, fix: bool = False) -> int:
    """Scan memories, report violations. If fix, delete vector experiences. Returns count of violations."""
    total = 0

    # Vector experiences
    try:
        exps = store.vector.list_all(limit=500)
        for e in exps:
            content = e.get("content", "")
            v = _violates_policy(content)
            if v:
                total += 1
                print(f"[experience] {e.get('id', '?')}: {v}")
                print(f"  Content: {content[:120]}...")
                if fix:
                    store.vector.delete([e.get("id", "")])
                    print("  -> deleted")
    except Exception as ex:
        print(f"Vector scan error: {ex}", file=sys.stderr)

    # Beliefs
    try:
        from rain.memory.belief_memory import list_beliefs
        for b in list_beliefs(store):
            claim = b.get("claim", "")
            v = _violates_policy(claim)
            if v:
                total += 1
                print(f"[belief] {b.get('key', '?')}: {v}")
                print(f"  Claim: {claim[:120]}...")
                if fix:
                    store.forget_fact(b.get("key", ""), kind="belief")
                    print("  -> deleted")
    except Exception as ex:
        print(f"Belief scan error: {ex}", file=sys.stderr)

    # Lessons
    try:
        facts = store.symbolic.get_all(kind="lesson")
        for f in facts:
            val = f.get("value")
            if isinstance(val, str):
                try:
                    import json
                    val = json.loads(val)
                except Exception:
                    val = {}
            sit = (val.get("situation", "") if isinstance(val, dict) else "") or ""
            v = _violates_policy(sit)
            if v:
                total += 1
                print(f"[lesson] {f.get('key', '?')}: {v}")
                print(f"  Situation: {sit[:120]}...")
                if fix:
                    store.forget_fact(f.get("key", ""), kind="lesson")
                    print("  -> deleted")
    except Exception as ex:
        print(f"Lesson scan error: {ex}", file=sys.stderr)

    return total


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Scan memories for policy violations")
    ap.add_argument("--fix", action="store_true", help="Delete flagged content (use with care)")
    args = ap.parse_args()

    store = MemoryStore(DATA_DIR)
    print("Scanning memories for policy violations...")
    n = run_hygiene(store, fix=args.fix)
    if n == 0:
        print("OK — no violations found.")
        return 0
    print(f"\nTotal: {n} violation(s) found.")
    if not args.fix:
        print("Run with --fix to delete (or use memory_audit.py retract/delete-exp for manual cleanup)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
