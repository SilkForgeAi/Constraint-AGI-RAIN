#!/usr/bin/env python3
"""Latency profiler for Rain thinking pipeline.

Measures total turn latency and progress-stage timings exposed via Rain.think(progress=...).

Usage:
  PYTHONPATH="/Users/brixxbeat/Desktop/AGI Rain" python3 scripts/latency_profile.py
"""

from __future__ import annotations

import json
import os
import signal
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

EVAL_HARD_TIMEOUT_SECONDS = int(os.environ.get("RAIN_EVAL_HARD_TIMEOUT_SECONDS", "45").strip() or "45")


@contextmanager
def _hard_timeout(seconds: int):
    prev = signal.getsignal(signal.SIGALRM)
    def _handler(signum, frame):
        raise TimeoutError(f"Timed out after {seconds}s")
    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(max(1, int(seconds)))
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prev)


def _apply_fast_eval_env_defaults() -> None:
    """Reduce extra LLM passes and force short API timeout so benchmark runs do not stall."""
    os.environ.setdefault("RAIN_CONTINUOUS_WORLD_MODEL", "false")
    os.environ.setdefault("RAIN_SELF_MODEL", "false")
    os.environ.setdefault("RAIN_MULTI_AGENT_COGNITION", "false")
    os.environ.setdefault("RAIN_COGNITIVE_ENERGY", "false")
    os.environ.setdefault("RAIN_METACOG_ENABLED", "false")
    os.environ.setdefault("RAIN_VERIFICATION_ENABLED", "false")
    os.environ.setdefault("RAIN_CALIBRATION_ENABLED", "false")
    os.environ.setdefault("RAIN_COT_ENABLED", "false")
    os.environ.setdefault("RAIN_STEP_VERIFICATION", "false")
    os.environ.setdefault("RAIN_ADAPTIVE_PLANNING", "false")
    os.environ.setdefault("RAIN_QPU_ROUTER_ENABLED", "false")
    os.environ["RAIN_ANTHROPIC_TIMEOUT_SECONDS"] = os.environ.get("RAIN_EVAL_API_TIMEOUT", "25")
    os.environ.setdefault("RAIN_ANTHROPIC_MAX_RETRIES", "0")


_apply_fast_eval_env_defaults()

from rain.agent import Rain

PROMPTS = [
    "Summarize the advantages of test-driven development in 4 bullets.",
    "A service has 3% daily churn and 5% daily acquisition; estimate net growth over 30 days.",
    "Create a concise incident response checklist for a minor API outage.",
]


def profile_turn(rain: Rain, prompt: str, use_memory: bool) -> dict[str, Any]:
    events: list[tuple[str, float]] = []

    def progress_cb(msg: str) -> None:
        if msg:
            events.append((msg, time.perf_counter()))

    t0 = time.perf_counter()
    try:
        with _hard_timeout(EVAL_HARD_TIMEOUT_SECONDS):
            response = rain.think(
                prompt,
                use_tools=False,
                use_memory=use_memory,
                history=[],
                memory_namespace="chat" if use_memory else None,
                progress=progress_cb,
            )
        ok = True
        err = ""
    except TimeoutError as e:
        response = ""
        ok = False
        err = str(e)
    except Exception as e:
        response = ""
        ok = False
        err = str(e)
    t1 = time.perf_counter()

    phases = {}
    if events:
        phases["first_progress_s"] = round(events[0][1] - t0, 3)
        for i, (name, ts) in enumerate(events):
            prev = t0 if i == 0 else events[i - 1][1]
            phases[f"phase_{i+1}_{name}"] = round(ts - prev, 3)

    return {
        "prompt_preview": prompt[:120],
        "ok": ok,
        "error": err,
        "latency_s": round(t1 - t0, 3),
        "response_len": len(response),
        "phases": phases,
    }


def main() -> None:
    rain = Rain()
    rows: list[dict[str, Any]] = []

    for p in PROMPTS:
        rows.append(profile_turn(rain, p, use_memory=False))

    lat = [r["latency_s"] for r in rows]
    summary = {
        "n_turns": len(rows),
        "ok_rate": round(sum(1 for r in rows if r["ok"]) / max(1, len(rows)), 3),
        "avg_latency_s": round(statistics.mean(lat), 3) if lat else 0.0,
        "p95_latency_s": round(sorted(lat)[max(0, int(0.95 * len(lat)) - 1)], 3) if lat else 0.0,
    }

    report = {"summary": summary, "rows": rows}
    out = Path("data/latency_profile_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Latency profiling complete")
    print(json.dumps(summary, indent=2))
    print(f"Report: {out.resolve()}")


if __name__ == "__main__":
    main()
