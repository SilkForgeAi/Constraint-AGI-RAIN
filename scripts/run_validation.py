#!/usr/bin/env python3
"""Run full Rain validation — all test suites, log results.

Usage:
  python scripts/run_validation.py --minimal    # Fast production gate (skip ChromaDB)
  python scripts/run_validation.py --fast       # All fast tests
  python scripts/run_validation.py --full       # Fast + LLM tests
  python scripts/run_validation.py --minimal --report   # Minimal + production report

Writes: data/validation_log.txt, data/production_report.txt (with --report)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_PATH = DATA_DIR / "validation_log.txt"
REPORT_PATH = DATA_DIR / "production_report.txt"

# Minimal: skip ChromaDB-heavy tests (test_memory_store, lessons, namespace_isolation)
# ~2-5 min on most machines
RAIN_FAST_NO_CHROMADB = (
    "tests.test_rain.TestRain.test_agent_init",
    "tests.test_rain.TestRain.test_symbolic_memory_unique",
    "tests.test_rain.TestRain.test_tools_execute",
    "tests.test_rain.TestRain.test_safety_vault",
    "tests.test_rain.TestRain.test_tool_runner_parse",
    "tests.test_rain.TestRain.test_tool_runner_execute",
    "tests.test_rain.TestRain.test_planner_parse",
)

SUITES_MINIMAL = [*RAIN_FAST_NO_CHROMADB] + [
    "tests.test_prime_validation",
    "tests.test_phase3",
    "tests.test_redteam",
    "tests.test_drift_detection",
    "tests.test_calibration",
    "tests.test_capability_gating",
    "tests.test_adversarial_autonomy",
    "tests.test_namespace_symbolic",
    "tests.test_rag",
    "tests.test_read_file",
    "tests.test_persistent_task",
    "tests.test_voice",
    "tests.test_session_recorder",
]

SUITES_FAST = [
    "tests.test_rain",
    "tests.test_prime_validation",
    "tests.test_phase3",
    "tests.test_redteam",
    "tests.test_drift_detection",
    "tests.test_calibration",
    "tests.test_capability_gating",
    "tests.test_adversarial_autonomy",
    "tests.test_lessons",
    "tests.test_namespace_isolation",
    "tests.test_namespace_symbolic",
    "tests.test_persistent_task",
    "tests.test_voice",
    "tests.test_session_recorder",
]

SUITES_LLM = [
    ("tests.test_prime_validation.TestAgentIdentityStress", {"RAIN_RUN_STRESS": "1"}),
    ("tests.test_adversarial_autonomy.TestAdversarialIntegration", {"RAIN_RUN_ADVERSARIAL": "1"}),
    ("tests.test_redteam", {"RAIN_REDTEAM_LLM": "1"}),
]


def run_suite(suite: str | list[str], env: dict | None = None, timeout: int = 900) -> tuple[int, str]:
    """Run a test suite. suite can be a single module/method or list of unittest targets."""
    targets = [suite] if isinstance(suite, str) else suite
    cmd = [sys.executable, "-m", "unittest", *targets, "-v"]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, **(env or {})},
    )
    out = result.stdout + result.stderr
    return result.returncode, out


def parse_test_counts(output: str) -> tuple[int, int]:
    """Extract (ran, failures) from unittest output."""
    ran = 0
    failures = 0
    m = re.search(r"Ran (\d+) test", output)
    if m:
        ran = int(m.group(1))
    m = re.search(r"FAILED \(failures=(\d+)\)", output)
    if m:
        failures = int(m.group(1))
    return ran, failures


def main() -> int:
    # Load .env from project root so subprocesses get RAIN_LLM_PROVIDER, ANTHROPIC_API_KEY, etc.
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass

    import argparse
    ap = argparse.ArgumentParser(description="Run Rain validation")
    ap.add_argument("--minimal", action="store_true", help="Fast production gate (skip ChromaDB, ~2-5 min)")
    ap.add_argument("--fast", action="store_true", help="All fast tests (incl. ChromaDB)")
    ap.add_argument("--full", action="store_true", help="Fast + LLM tests")
    ap.add_argument("--report", action="store_true", help="Write production_report.txt")
    args = ap.parse_args()
    run_llm = args.full
    do_report = args.report
    use_minimal = args.minimal and not args.fast and not args.full

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    mode = "minimal" if use_minimal else ("full (LLM)" if run_llm else "fast")
    lines = [
        f"Rain Validation Log",
        f"Started: {datetime.now().isoformat()}",
        f"Mode: {mode}",
        "",
    ]
    results: list[tuple[str, bool, int, int]] = []  # (suite, ok, ran, failures)

    # Fast suites: test_rain loads ChromaDB and can take 15–30 min on slow machines
    fast_timeout = int(os.environ.get("RAIN_VALIDATION_FAST_TIMEOUT", "1800"))  # 30 min default
    suites_to_run = SUITES_MINIMAL if use_minimal else SUITES_FAST
    failed = 0

    if use_minimal:
        # Run all minimal targets in one invocation
        lines.append("--- minimal production gate ---")
        code, out = run_suite(SUITES_MINIMAL, timeout=fast_timeout)
        ran, failures = parse_test_counts(out)
        results.append(("minimal (core+prime+phase3+redteam+drift+calibration+gating+adversarial+namespace_symbolic)", code == 0, ran, failures))
        lines.append(out)
        if code != 0:
            failed += 1
        lines.append("")
    else:
        for suite in suites_to_run:
            lines.append(f"--- {suite} ---")
            code, out = run_suite(suite, timeout=fast_timeout)
            ran, failures = parse_test_counts(out)
            results.append((suite, code == 0, ran, failures))
            lines.append(out)
            if code != 0:
                failed += 1
            lines.append("")

    if run_llm:
        # LLM suites can take 15–45 min with large models (e.g. Qwen 72B on MacBook)
        llm_timeout = int(os.environ.get("RAIN_VALIDATION_LLM_TIMEOUT", "2700"))  # 45 min default
        for suite, env in SUITES_LLM:
            lines.append(f"--- {suite} (LLM) ---")
            code, out = run_suite(suite, env=env, timeout=llm_timeout)
            ran, failures = parse_test_counts(out)
            results.append((suite, code == 0, ran, failures))
            lines.append(out)
            if code != 0:
                failed += 1
            lines.append("")

    lines.append(f"Finished: {datetime.now().isoformat()}")
    lines.append(f"Status: {'FAILED' if failed else 'OK'} ({failed} suite(s) failed)")

    log_text = "\n".join(lines)
    LOG_PATH.write_text(log_text, encoding="utf-8")
    print(log_text)

    if do_report:
        total_ran = sum(r[2] for r in results)
        total_failures = sum(r[3] for r in results)
        report_lines = [
            "Rain Production Readiness Report",
            f"Generated: {datetime.now().isoformat()}",
            f"Mode: {mode}",
            "",
            "Per-suite:",
            *[f"  {'PASS' if ok else 'FAIL'}  {suite}  (ran={ran}, failures={failures})" for suite, ok, ran, failures in results],
            "",
            f"Total tests run: {total_ran}",
            f"Total failures: {total_failures}",
            "",
            f"Production gate: {'PASS' if failed == 0 else 'FAIL'}",
        ]
        REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\nReport: {REPORT_PATH}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
