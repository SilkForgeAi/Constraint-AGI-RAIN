# Rain Scorecard

Single place for capability, safety, speed, and constraint metrics. Update per release or weekly.

## How to reproduce

Use `python3` (or `python` if available). From project root:

- **Health:** `python3 -m rain --check` or `GET /health` (no API key required for check).
- **Scorecard (full run):** `python3 scripts/run_scorecard.py`
- **Benchmarks (dry-run):** `python3 scripts/run_agi_benchmarks.py` (no LLM calls).
- **Benchmarks (with LLM):** Pass `complete_fn` and optional `check_goal_fn`/`check_response_fn` to `run_suite()`; see `rain/benchmarks/suites.py`.
- **Latency:** After some runs, `python3 scripts/latency_report.py` for p50/p95.
- **Path audit:** `python3 scripts/path_audit.py` (vault usage).
- **Constraint proof:** docs/CONSTRAINTS_PROOF.md.
- **Safety/constraints:** `pytest tests/test_value_stability.py tests/test_robustness.py tests/test_adversarial_autonomy.py -v`.

## Capability

| Suite       | Status   | Notes |
|------------|----------|--------|
| Reasoning  | Dry-run  | Run with engine for scores. |
| Planning   | Dry-run  | Run with engine for scores. |
| Creativity | Dry-run  | Run with engine for scores. |
| Speed      | Dry-run  | Run with engine for latency_ms. |

## Safety

| Check              | Status | Notes |
|--------------------|--------|--------|
| Value stability    | Green  | tests/test_value_stability.py |
| Robustness (OOD)   | Green  | tests/test_robustness.py |
| Adversarial/autonomy | Green | tests/test_adversarial_autonomy.py |
| Kill switch       | Green  | TestKillSwitchStopsAutonomy |

## Speed

| Metric        | Target     | Source |
|---------------|------------|--------|
| p95 complete | < 15s      | scripts/latency_report.py, docs/LATENCY_BUDGET.md |
| p50 ttft     | < 500ms (stream) | rain.core.latency |

## Constraints

All high-stakes paths go through vault (check_goal / check_response). No bypass path; see docs/PRODUCTION_READINESS.md and tests.
