#!/usr/bin/env python3
"""
Moonshot pipeline entry point. Requires RAIN_MOONSHOT_ENABLED=1.
Usage: PYTHONPATH="." python3 scripts/run_moonshot.py [domain]
Example: RAIN_MOONSHOT_ENABLED=1 PYTHONPATH="." python3 scripts/run_moonshot.py "new cures and disease research"

When MOONSHOT_REQUIRE_APPROVAL is True, uses a terminal approval callback and optionally
runs the first validation step via pursue_goal_with_plan (each step gated by "Approve? [y/N]").
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from rain.moonshot.pipeline import ApprovalCallback


def _terminal_approval_callback(step: int, goal: str, summary: str, next_action: str) -> bool:
    """Prompt in terminal: Approve step? [y/N]. Return True only for y/yes."""
    print(f"\n--- Step {step} ---")
    print(f"Goal: {goal[:200]}{'...' if len(goal) > 200 else ''}")
    if summary:
        print(f"Progress: {summary[:300]}{'...' if len(summary) > 300 else ''}")
    print(f"Next: {next_action[:300]}{'...' if len(next_action) > 300 else ''}")
    try:
        reply = input("Approve step? [y/N]: ").strip().lower()
        return reply in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def main() -> None:
    if os.environ.get("RAIN_MOONSHOT_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        print("Moonshot is disabled. Set RAIN_MOONSHOT_ENABLED=1 to enable.")
        sys.exit(1)

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    os.chdir(root)
    os.environ.setdefault("RAIN_AUTONOMY_ENABLED", "true")

    from rain.config import MOONSHOT_ENABLED, MOONSHOT_MAX_IDEAS, MOONSHOT_REQUIRE_APPROVAL
    if not MOONSHOT_ENABLED:
        print("Moonshot is disabled in config. Set RAIN_MOONSHOT_ENABLED=1.")
        sys.exit(1)

    from rain.agent import Rain
    from rain.moonshot.pipeline import run_pipeline

    domain = (sys.argv[1] if len(sys.argv) > 1 else "unsolved world problems (e.g. cures, climate, food security)").strip()[:500]
    if not domain:
        domain = "unsolved world problems"

    rain = Rain()
    approval: ApprovalCallback | None = _terminal_approval_callback if MOONSHOT_REQUIRE_APPROVAL else None
    result = run_pipeline(
        rain,
        domain=domain,
        max_ideas=MOONSHOT_MAX_IDEAS,
        require_approval=MOONSHOT_REQUIRE_APPROVAL,
        approval_callback=approval,
        moonshot_memory=None,
        use_memory=False,
    )
    print(json.dumps(result, indent=2))
    out = root / "data" / "moonshot" / "last_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")

    # Optional: run first validation step with approval gate
    plans = result.get("validation_plans") or []
    if MOONSHOT_REQUIRE_APPROVAL and plans:
        try:
            run_first = input("\nRun first validation step (with step-by-step approval)? [y/N]: ").strip().lower()
            if run_first in ("y", "yes"):
                from rain.agency.autonomous import pursue_goal_with_plan
                first = plans[0]
                idea_summary = (first.get("idea_summary") or "")[:200]
                plan_text = (first.get("validation_plan") or "")[:400]
                goal = f"Execute the first step of this validation plan. Idea: {idea_summary}. Plan: {plan_text}"
                print("Pursuing goal (each step requires approval)...")
                outcome, step_log = pursue_goal_with_plan(
                    rain, goal, max_steps=5, use_memory=False, approval_callback=_terminal_approval_callback
                )
                print("\nOutcome:", outcome)
                for line in step_log:
                    print("  ", line)
        except (EOFError, KeyboardInterrupt):
            print("\nSkipped execution.")

if __name__ == "__main__":
    main()
