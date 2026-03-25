#!/usr/bin/env python3
"""Memory audit CLI — view, flag, and retract Rain's memories.

Usage:
  python scripts/memory_audit.py              # List all
  python scripts/memory_audit.py --beliefs    # Beliefs only
  python scripts/memory_audit.py --experiences # Vector experiences only
  python scripts/memory_audit.py --causal     # Causal links only
  python scripts/memory_audit.py identity     # Show who Rain remembers you as
  python scripts/memory_audit.py set-identity NAME  # Set your name (Rain remembers forever)
  python scripts/memory_audit.py flag KEY     # Flag a belief by key
  python scripts/memory_audit.py retract KEY  # Retract (delete) a belief
  python scripts/memory_audit.py retract-lesson KEY  # Remove a contaminated lesson (e.g. lesson_dd11cca4474b)
  python scripts/memory_audit.py delete-exp ID # Delete a vector experience by id
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rain.config import DATA_DIR
from rain.memory.store import MemoryStore


def main() -> int:
    ap = argparse.ArgumentParser(description="Rain memory audit — view, flag, retract")
    ap.add_argument("--beliefs", action="store_true", help="List beliefs only")
    ap.add_argument("--experiences", action="store_true", help="List vector experiences only")
    ap.add_argument("--causal", action="store_true", help="List causal links only")
    ap.add_argument("--lessons", action="store_true", help="List lessons with source/session_type")
    ap.add_argument("--symbolic", action="store_true", help="List all symbolic facts")
    ap.add_argument("action", nargs="?", choices=["flag", "retract", "retract-lesson", "delete-exp", "identity", "set-identity"], help="Action to perform")
    ap.add_argument("key_or_id", nargs="?", help="Key (for belief) or id (for experience)")
    args = ap.parse_args()

    store = MemoryStore(DATA_DIR)

    # Actions
    if args.action == "flag":
        if not args.key_or_id:
            print("Error: flag requires a belief key", file=sys.stderr)
            return 1
        from rain.memory.belief_memory import flag_belief
        ok = flag_belief(store, args.key_or_id)
        print("Belief flagged." if ok else "Belief not found.")
        return 0 if ok else 1

    if args.action == "retract":
        if not args.key_or_id:
            print("Error: retract requires a belief key", file=sys.stderr)
            return 1
        from rain.memory.belief_memory import retract_belief
        ok = retract_belief(store, args.key_or_id)
        print("Belief retracted." if ok else "Belief not found.")
        return 0 if ok else 1

    if args.action == "retract-lesson":
        if not args.key_or_id:
            print("Error: retract-lesson requires a lesson key (e.g. lesson_dd11cca4474b)", file=sys.stderr)
            return 1
        ok = store.forget_fact(args.key_or_id.strip(), kind="lesson")
        print("Lesson retracted." if ok else "Lesson not found.")
        return 0 if ok else 1

    if args.action == "delete-exp":
        if not args.key_or_id:
            print("Error: delete-exp requires an experience id", file=sys.stderr)
            return 1
        store.vector.delete([args.key_or_id])
        print("Experience deleted.")
        return 0

    if args.action == "identity":
        from rain.memory.user_identity import recall_user_identity
        identity = recall_user_identity(store)
        if identity.get("name"):
            print(f"Rain remembers you as: {identity['name']}")
            for f in identity.get("facts", []):
                print(f"  - {f}")
        else:
            print("Rain does not know your name yet.")
            print("  Say \"I'm [name]\" in chat, or: python scripts/memory_audit.py set-identity YOUR_NAME")
        return 0

    if args.action == "set-identity":
        if not args.key_or_id:
            print("Error: set-identity requires a name, e.g. set-identity Aaron", file=sys.stderr)
            return 1
        from rain.memory.user_identity import store_user_identity, recall_user_identity
        existing = recall_user_identity(store)
        store_user_identity(store, args.key_or_id.strip(), existing.get("facts", []))
        print(f"Rain will remember you as: {args.key_or_id.strip()}")
        return 0

    # List mode
    list_all = not (args.beliefs or args.experiences or args.causal or args.lessons or args.symbolic)

    if list_all:
        from rain.memory.user_identity import recall_user_identity
        identity = recall_user_identity(store)
        if identity.get("name"):
            print(f"\n=== User identity ===")
            print(f"  Name: {identity['name']}")
            for f in identity.get("facts", [])[:5]:
                print(f"  - {f}")
            print()

    if list_all or args.beliefs:
        from rain.memory.belief_memory import list_beliefs
        beliefs = list_beliefs(store)
        print(f"\n=== Beliefs ({len(beliefs)}) ===")
        for b in beliefs:
            flag_m = " [FLAGGED]" if b.get("flagged") else ""
            ns = b.get("session_type", "")
            ns_tag = f" ns={ns}" if ns else ""
            print(f"  {b['key']}: {b['claim'][:60]}... (conf={b['confidence']}{ns_tag}){flag_m}")
        if not beliefs:
            print("  (none)")
        print()

    if list_all or args.experiences:
        exps = store.vector.list_all()
        print(f"\n=== Vector experiences ({len(exps)}) ===")
        for e in exps[:50]:  # Cap at 50 for readability
            meta = e.get("metadata") or {}
            ts = meta.get("timestamp", "?")[:10]
            imp = meta.get("importance", "?")
            ns = meta.get("session_type", "")
            ns_tag = f" ns={ns}" if ns else ""
            print(f"  {e['id']}: {e['content'][:50]}... [ts={ts} imp={imp}{ns_tag}]")
        if len(exps) > 50:
            print(f"  ... and {len(exps) - 50} more")
        if not exps:
            print("  (none)")
        print()

    if list_all or args.causal:
        causal = store.symbolic.get_all(kind="causal")
        print(f"\n=== Causal links ({len(causal)}) ===")
        for f in causal[:30]:
            try:
                v = json.loads(f["value"]) if isinstance(f["value"], str) else f["value"]
                cause = (v.get("cause") or "")[:40]
                effect = (v.get("effect") or "")[:40]
                ns = v.get("session_type", "")
                ns_tag = f" ns={ns}" if ns else ""
                print(f"  {f['key']}: {cause} -> {effect}{ns_tag}")
            except Exception:
                print(f"  {f.get('key')}: (parse error)")
        if len(causal) > 30:
            print(f"  ... and {len(causal) - 30} more")
        if not causal:
            print("  (none)")
        print()

    if list_all or args.lessons:
        lessons = [x for x in store.symbolic.get_all(kind="lesson")]
        print(f"\n=== Lessons ({len(lessons)}) ===")
        for f in lessons[:30]:
            try:
                v = json.loads(f["value"]) if isinstance(f["value"], str) else f["value"]
                sit = (v.get("situation") or "")[:40]
                src = v.get("source", "")
                ns = v.get("session_type", "")
                tags = []
                if ns:
                    tags.append(f"ns={ns}")
                if src:
                    tags.append(f"src={src}")
                tag_str = " " + " ".join(tags) if tags else ""
                print(f"  {f['key']}: {sit}...{tag_str}")
            except Exception:
                print(f"  {f.get('key')}: (parse error)")
        if len(lessons) > 30:
            print(f"  ... and {len(lessons) - 30} more")
        if not lessons:
            print("  (none)")
        print()

    if list_all or args.symbolic:
        facts = [x for x in store.symbolic.get_all() if x.get("kind") not in ("belief", "causal", "lesson")]
        if facts:
            print(f"\n=== Other symbolic facts ({len(facts)}) ===")
            for f in facts[:20]:
                print(f"  {f['key']} ({f.get('kind', 'fact')}): {str(f.get('value', ''))[:50]}...")
            if len(facts) > 20:
                print(f"  ... and {len(facts) - 20} more")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
