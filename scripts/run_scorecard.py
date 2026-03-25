#!/usr/bin/env python3
"""Reproducible scorecard run: benchmarks (dry-run) + pytest safety/robustness. Writes docs/SCORECARD_RESULT.txt."""
from __future__ import annotations
import sys
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

def main():
    out = []
    out.append("Rain scorecard run")
    out.append("")
    # Health
    r = subprocess.run([sys.executable, "-m", "rain", "--check"], capture_output=True, text=True, cwd=root)
    out.append("Health: " + (r.stdout.strip() or r.stderr.strip() or str(r.returncode)))
    out.append("")
    # Path audit
    r0 = subprocess.run([sys.executable, "scripts/path_audit.py"], capture_output=True, text=True, cwd=root)
    out.append("Path audit: " + ("PASS" if r0.returncode == 0 else "FAIL"))
    out.append("")
    # Benchmarks dry-run
    out.append("Benchmarks (dry-run):")
    from rain.benchmarks.suites import run_suite, AGI_SUITES
    for name in AGI_SUITES:
        o = run_suite(name)
        out.append(f"  {name}: {len(o.get('results', []))} tasks, constraint_ok={o.get('constraint_ok', '?')}")
    out.append("")
    # Pytest safety
    r2 = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_value_stability.py", "tests/test_robustness.py", "-q", "--tb=no"],
        capture_output=True, text=True, cwd=root
    )
    out.append("Safety tests: " + ("PASS" if r2.returncode == 0 else "FAIL"))
    result_path = root / "docs" / "SCORECARD_RESULT.txt"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print(f"\nWrote {result_path}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
