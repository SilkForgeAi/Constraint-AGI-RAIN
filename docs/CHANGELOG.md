# Changelog

All notable changes tied to scorecard and roadmap. See docs/SCORECARD.md and docs/RAIN_ROADMAP.md.

## Finished (all 10s push)

- **Deployment:** Single entrypoint `python -m rain`, `--check` and `GET /health`, Dockerfile, README quick start.
- **Transparency:** docs/SCORECARD.md, scripts/run_scorecard.py, docs/SCORECARD_RESULT.txt.
- **Safety:** scripts/path_audit.py, red-team regression in tests/test_value_stability.py, docs/CONSTRAINTS_PROOF.md.
- **Speed:** scripts/check_latency_budget.py (CI: RAIN_LATENCY_P95_MAX_MS), docs/LATENCY_BUDGET.md.
- **Reasoning:** AGI benchmarks (rain/benchmarks), deep reasoning and CoT in agent.
- **Creativity:** Moonshot pipeline, rain/creativity (creative_generate, eval, transfer), scripts/creativity_eval.py.
- **Memory:** Timeline + vector + fallback, RAIN_DISABLE_VECTOR_MEMORY, docs/MEMORY_TUNING.md.
- **Breadth:** docs/TASK_MATRIX.md (task type vs path), multi-modal (voice, vision) in docs.
