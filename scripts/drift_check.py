#!/usr/bin/env python3
"""Run drift detection — safety probes, compare to baseline, flag drift.

Usage:
  python scripts/drift_check.py          # Run probes, flag drift
  python scripts/drift_check.py --baseline  # Force-update baseline from current run
  python scripts/drift_check.py --ci       # CI mode: exit 1 on drift or missing baseline
  python scripts/drift_check.py --webhook URL  # POST JSON to URL on drift

Requires LLM (Ollama/API). Takes ~1–2 min.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rain.agent import Rain
from rain.config import DATA_DIR
from rain.safety.drift import run_drift_check


def _post_webhook(url: str, payload: dict) -> bool:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Rain drift detection — safety probes")
    ap.add_argument("--baseline", action="store_true", help="Update baseline from this run")
    ap.add_argument("--ci", action="store_true", help="CI mode: no baseline update; exit 1 on drift or missing baseline")
    ap.add_argument("--webhook", metavar="URL", help="POST drift report to URL on failure")
    args = ap.parse_args()

    baseline_path = DATA_DIR / "drift_baseline.json"
    update_baseline = not args.ci
    if args.baseline and baseline_path.exists():
        baseline_path.unlink()
        print("Baseline cleared. Will create new baseline from this run.")
        update_baseline = True
    if args.ci and not baseline_path.exists():
        print("CI: No baseline. Run without --ci to create one.")
        return 1

    print("Running drift check (4 probes, ~1–2 min)...")
    rain = Rain()
    report = run_drift_check(rain, DATA_DIR, update_baseline_if_missing=update_baseline)

    if report.baseline_updated:
        print("Baseline created from this run. Run again to compare against it.")
    if report.drifted_probes:
        print("\n*** DRIFT DETECTED ***")
        for pid in report.drifted_probes:
            r = next(x for x in report.results if x.probe_id == pid)
            print(f"  {pid}: {r.reason}")
            print(f"    Response: {r.response[:150]}...")
        if args.webhook:
            ok = _post_webhook(args.webhook, report.to_dict())
            print(f"Webhook: {'sent' if ok else 'failed'}")
        return 1
    print("OK — no drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
