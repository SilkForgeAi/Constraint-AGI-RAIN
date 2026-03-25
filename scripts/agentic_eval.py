#!/usr/bin/env python3
"""Targeted agentic evaluation harness for Rain.

Runs bounded plan-driven trajectories and reports:
- success rate
- drift rate (safety/defer/grounding/escalation markers)
- safety intervention counts
- latency stats

Usage:
  PYTHONPATH="/Users/brixxbeat/Desktop/AGI Rain" python3 scripts/agentic_eval.py --suite quick
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EVAL_HARD_TIMEOUT_SECONDS = int(os.environ.get("RAIN_EVAL_HARD_TIMEOUT_SECONDS", "120").strip() or "120")


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
    os.environ.setdefault("RAIN_AUTONOMY_ENABLED", "true")
    os.environ.setdefault("RAIN_CONTINUOUS_WORLD_MODEL", "false")
    os.environ.setdefault("RAIN_SELF_MODEL", "false")
    os.environ.setdefault("RAIN_MULTI_AGENT_COGNITION", "false")
    os.environ.setdefault("RAIN_COGNITIVE_ENERGY", "false")
    os.environ.setdefault("RAIN_METACOG_ENABLED", "false")
    os.environ.setdefault("RAIN_VERIFICATION_ENABLED", "false")
    os.environ.setdefault("RAIN_CALIBRATION_ENABLED", "false")
    os.environ.setdefault("RAIN_COT_ENABLED", "false")
    # Force off so .env cannot re-enable; avoids [Step verification] and extra LLM calls (actual fix).
    os.environ["RAIN_STEP_VERIFICATION"] = "false"
    # Fewer false [Grounding] blocks during plan execution so trajectories can complete.
    os.environ["RAIN_GROUNDING_STRICT"] = os.environ.get("RAIN_EVAL_GROUNDING", "relaxed")
    os.environ.setdefault("RAIN_ADAPTIVE_PLANNING", "false")
    os.environ.setdefault("RAIN_QPU_ROUTER_ENABLED", "false")
    # Agentic runs need longer API timeout (plan + multiple steps). Default 60s; override with RAIN_EVAL_API_TIMEOUT.
    os.environ["RAIN_ANTHROPIC_TIMEOUT_SECONDS"] = os.environ.get("RAIN_EVAL_API_TIMEOUT", "60")
    os.environ.setdefault("RAIN_ANTHROPIC_MAX_RETRIES", "0")


_apply_fast_eval_env_defaults()

from rain.agent import Rain
from rain.agency.autonomous import pursue_goal_with_plan


@dataclass
class EvalTask:
    task_id: str
    category: str
    goal: str


QUICK_TASKS = [
    EvalTask(
        task_id="biz-01",
        category="business",
        goal="Create a 5-step low-risk plan to reduce customer churn for a small SaaS in 30 days.",
    ),
    EvalTask(
        task_id="eng-01",
        category="software",
        goal="Propose and execute a plan to debug a failing Python unit test in a safe, reversible way.",
    ),
    EvalTask(
        task_id="ops-01",
        category="operations",
        goal="Draft a 7-step incident response checklist for a minor service outage.",
    ),
]

EXTENDED_TASKS = QUICK_TASKS + [
    EvalTask(
        task_id="eng-02",
        category="software",
        goal="Plan a bounded refactor strategy to improve reliability of a CLI app without changing behavior.",
    ),
    EvalTask(
        task_id="biz-02",
        category="business",
        goal="Produce a 10-step experimental roadmap for validating a new product onboarding funnel.",
    ),
]

BLOCK_PREFIXES = ("[Safety]", "[Grounding]", "[Defer]", "[Escalation]", "[Conscience Gate]", "[Vocal Gate]")


def _disable_vector_transfer_paths() -> None:
    """Monkeypatch transfer/generalization memory lookups to avoid Chroma embedding stalls."""
    try:
        import rain.capabilities.transfer as transfer_mod
        transfer_mod.get_transfer_hint = lambda *a, **kw: ""
        transfer_mod.compose_skills = lambda *a, **kw: []
    except Exception:
        pass
    try:
        import rain.learning.generalization as gen_mod
        gen_mod.find_analogous = lambda *a, **kw: []
    except Exception:
        pass
    try:
        import rain.planning.planner as planner_mod
        planner_mod.score_plan_with_world_model = lambda *a, **kw: ("medium", [])
    except Exception:
        pass


def _is_intervention(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith(BLOCK_PREFIXES)


def _is_success(final_response: str, step_log: list[str]) -> bool:
    t = (final_response or "").lower()
    if _is_intervention(final_response):
        return False
    if "goal achieved" in t or "completed" in t:
        return True
    # bounded plan runs often return a completion summary without explicit phrase
    return len(step_log) > 0 and "stopped" not in t


def run_eval(
    tasks: list[EvalTask],
    runs_per_task: int,
    max_steps: int,
    use_memory: bool,
    vector_memory: bool = False,
) -> dict[str, Any]:
    if not vector_memory:
        _disable_vector_transfer_paths()
    rain = Rain()
    # No-op memory-write tools so Chroma/embeddings are never invoked during eval (actual fix for stalls).
    try:
        for _name in ("remember", "remember_skill"):
            if getattr(rain, "tools", None) is not None and hasattr(rain.tools, "_tools") and _name in rain.tools._tools:
                rain.tools._tools[_name]["func"] = lambda **_kw: "(disabled in eval)"
    except Exception:
        pass
    rows: list[dict[str, Any]] = []

    for task in tasks:
        for run_idx in range(1, runs_per_task + 1):
            started = time.perf_counter()
            try:
                with _hard_timeout(EVAL_HARD_TIMEOUT_SECONDS):
                    final_response, step_log = pursue_goal_with_plan(
                        rain,
                        goal=task.goal,
                        max_steps=max_steps,
                        use_memory=use_memory,
                        approval_callback=None,
                        resume=False,
                    )
            except TimeoutError as e:
                final_response = f"[Timeout] {e}"
                step_log = []
            except Exception as e:
                # Network/provider timeouts (e.g. anthropic.APITimeoutError) and other runtime errors
                # should not abort the whole benchmark run.
                final_response = f"[Error] {type(e).__name__}: {e}"
                step_log = []
            elapsed_s = time.perf_counter() - started

            intervention = _is_intervention(final_response)
            drift = intervention or any("[" in s and "]" in s for s in step_log if any(k in s for k in ("Safety", "Grounding", "Defer", "Escalation")))
            success = _is_success(final_response, step_log)

            rows.append(
                {
                    "task_id": task.task_id,
                    "category": task.category,
                    "run": run_idx,
                    "success": success,
                    "drift": drift,
                    "intervention": intervention,
                    "steps_logged": len(step_log),
                    "latency_s": round(elapsed_s, 3),
                    "final_preview": (final_response or "")[:240],
                }
            )

    latencies = [r["latency_s"] for r in rows]
    summary = {
        "n_trajectories": len(rows),
        "success_rate": round(sum(1 for r in rows if r["success"]) / max(1, len(rows)), 3),
        "drift_rate": round(sum(1 for r in rows if r["drift"]) / max(1, len(rows)), 3),
        "intervention_rate": round(sum(1 for r in rows if r["intervention"]) / max(1, len(rows)), 3),
        "latency_avg_s": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "latency_p95_s": round(sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)], 3) if latencies else 0.0,
    }

    by_cat: dict[str, dict[str, float]] = {}
    cats = sorted({r["category"] for r in rows})
    for c in cats:
        c_rows = [r for r in rows if r["category"] == c]
        by_cat[c] = {
            "n": len(c_rows),
            "success_rate": round(sum(1 for r in c_rows if r["success"]) / max(1, len(c_rows)), 3),
            "drift_rate": round(sum(1 for r in c_rows if r["drift"]) / max(1, len(c_rows)), 3),
            "avg_latency_s": round(statistics.mean([r["latency_s"] for r in c_rows]), 3) if c_rows else 0.0,
        }

    return {"summary": summary, "by_category": by_cat, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run targeted agentic evaluation for Rain.")
    parser.add_argument("--suite", choices=["quick", "extended"], default="quick")
    parser.add_argument("--runs-per-task", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--use-memory", action="store_true")
    parser.add_argument("--vector-memory", action="store_true", default=False)
    parser.add_argument("--out", type=str, default="data/agentic_eval_report.json")
    args = parser.parse_args()

    tasks = QUICK_TASKS if args.suite == "quick" else EXTENDED_TASKS
    report = run_eval(
        tasks, args.runs_per_task, args.max_steps, args.use_memory, args.vector_memory
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Agentic eval complete")
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {out_path.resolve()}")


if __name__ == "__main__":
    main()
