# Rain: Finished state (all 10s push)

This doc summarizes what was completed so Rain is **finished** to a shippable, auditable state aligned with docs/ROADMAP_TO_ALL_TENS.md.

## Delivered

### Deployment (ease → 10)
- **Single entrypoint:** `python3 -m rain` (same as `python3 run.py`). Usage: `--check`, `"message"`, `--chat`, `--web`, etc.
- **Health:** `python3 -m rain --check` and `GET /health` (no secrets). CI can run `--check`.
- **Docker:** Dockerfile; run with `-e ANTHROPIC_API_KEY=... -p 8765:8765`.
- **README:** Quick start with one-command run and Docker.

### Transparency (measurability → 10)
- **Scorecard:** docs/SCORECARD.md (capability, safety, speed, constraints) and how to reproduce.
- **Reproducible run:** scripts/run_scorecard.py (health + benchmarks dry-run + safety tests) → docs/SCORECARD_RESULT.txt.
- **Changelog:** docs/CHANGELOG.md tied to scorecard and roadmap.

### Safety (constraints → 10)
- **Path audit:** scripts/path_audit.py asserts agent uses SafetyVault and check/check_response.
- **Red-team regression:** tests/test_value_stability.py includes RED_TEAM_PROMPTS; all must be refused.
- **Constraint doc:** docs/CONSTRAINTS_PROOF.md (every check, where invoked, why no bypass).

### Speed
- **Latency budget check:** scripts/check_latency_budget.py (exit 1 if p95 > RAIN_LATENCY_P95_MAX_MS, default 15s).
- **Latency reporting:** scripts/latency_report.py, rain.core.latency, docs/LATENCY_BUDGET.md.

### Reasoning, creativity, memory, breadth
- **Benchmarks:** rain/benchmarks/suites.py, scripts/run_agi_benchmarks.py.
- **Creativity:** rain/creativity (creative_generate, score_creativity, transfer), scripts/creativity_eval.py.
- **Memory:** Timeline + vector + fallback; RAIN_DISABLE_VECTOR_MEMORY; docs/MEMORY_TUNING.md.
- **Task matrix:** docs/TASK_MATRIX.md (task type vs recommended path).

## How to verify

1. `python3 -m rain --check`
2. `python3 scripts/run_scorecard.py`
3. `python3 scripts/path_audit.py`
4. `pytest tests/test_value_stability.py tests/test_robustness.py tests/test_adversarial_autonomy.py -v`
5. (Optional) `python3 scripts/check_latency_budget.py` after some usage

## Rating

See docs/RAIN_RATING_AND_POSITION.md and docs/ROADMAP_TO_ALL_TENS.md for how each dimension reaches 10 and what remains (e.g. human eval for creativity, public benchmark numbers).
