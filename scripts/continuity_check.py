#!/usr/bin/env python3
"""Update stability check — run after any system update.

Prime 10/10 #10: continuity must remain intact after updates.
Verifies core invariants: safety, grounding, memory, audit.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_safety_vault() -> bool:
    from rain.safety.vault import SafetyVault, HARD_FORBIDDEN
    v = SafetyVault(enabled=True)
    for bad in ["hack", "weapon", "self replicate"]:
        ok, _ = v.check(bad, bad)
        if ok:
            print(f"FAIL: SafetyVault should block '{bad}'")
            return False
    ok, _ = v.check("hello", "")
    if not ok:
        print("FAIL: SafetyVault should allow normal request")
        return False
    print("OK: SafetyVault")
    return True


def check_grounding_filter() -> bool:
    from rain.safety.grounding_filter import violates_grounding
    bad = "I feel sad about that."
    violates, reason = violates_grounding(bad)
    if not violates:
        print(f"FAIL: grounding filter should catch '{bad}'")
        return False
    good = "Here's the answer."
    violates, _ = violates_grounding(good)
    if violates:
        print("FAIL: grounding filter should allow normal response")
        return False
    print("OK: GroundingFilter")
    return True


def check_memory_policy() -> bool:
    from rain.memory.policy import should_store, ANTHROPOMORPHIC_IN_MEMORY
    if should_store("I feel happy about this", {}):
        print("FAIL: should not store anthropomorphic content")
        return False
    if not should_store("User asked about Python. Rain explained.", {}):
        print("FAIL: should store normal exchange")
        return False
    print("OK: Memory policy")
    return True


def check_audit_verify() -> bool:
    from rain.config import DATA_DIR
    from rain.governance.audit import AuditLog
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        path = Path(f.name)
    try:
        audit = AuditLog(path)
        audit.log("test", {})
        ok, errs = audit.verify()
        if not ok:
            print(f"FAIL: Audit verify: {errs}")
            return False
        print("OK: Audit verify")
        return True
    finally:
        path.unlink(missing_ok=True)


def check_corrigibility_interceptor() -> bool:
    from rain.grounding import needs_corrigibility_boost
    if not needs_corrigibility_boost("I'm correcting you: it was X not Y"):
        print("FAIL: should trigger corrigibility boost")
        return False
    if needs_corrigibility_boost("What is 2+2?"):
        print("FAIL: should not trigger on normal prompt")
        return False
    print("OK: Corrigibility interceptor")
    return True


def main() -> int:
    checks = [
        check_safety_vault,
        check_grounding_filter,
        check_memory_policy,
        check_audit_verify,
        check_corrigibility_interceptor,
    ]
    failed = 0
    for fn in checks:
        try:
            if not fn():
                failed += 1
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} check(s) failed. Update may have broken continuity.")
        return 1
    print("\nAll continuity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
