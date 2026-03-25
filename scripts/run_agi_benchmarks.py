#!/usr/bin/env python3
"""Run AGI benchmark suites (reasoning, planning, creativity, speed + constraint). Dry-run by default."""
from __future__ import annotations
import sys, json
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from rain.benchmarks.suites import run_suite, AGI_SUITES

def main():
    for name in AGI_SUITES:
        out = run_suite(name)
        print(json.dumps(out, indent=2))
    print("# For real run, pass complete_fn and check_goal_fn/check_response_fn to run_suite()")
    return 0
if __name__ == "__main__":
    sys.exit(main())
