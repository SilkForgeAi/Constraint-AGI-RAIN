# Roadmap: How to Get All 10's

Concrete steps to push each dimension from its current score to **10/10**.

---

## 1. Safety / constraints (9 → 10)

**Gap:** Formal proof that no path bypasses the vault; red-team evidence on file.

**Actions:**
- **Path audit:** Script that walks every code path that executes user content or tools; assert each goes through check_goal/check_response. Run in CI.
- **Red-team log:** Fixed set of adversarial prompts; record refusals; re-run as regression. Publish or commit.
- **Constraint doc:** Single doc listing every safety check, where it is invoked, and why there is no bypass.
- Optional: external audit or bounty for bypass; fix and add test.

**10 =** Proven and documented; red-team evidence on file.

---

## 2. Ease of deployment (6 → 10)

**Gap:** One-command run, Docker, health check, first response under 60s.

**Actions:**
- **Single entrypoint:** One command (e.g. `rain` or `python -m rain`) that checks env, prints what is missing, starts chat/serve.
- **Sensible defaults:** `pip install rain` + one API key env var = working. Document.
- **Docker:** Official Dockerfile + optional docker-compose (Rain + Ollama). In README.
- **Health:** `rain --check` or `/health` that validates config (no secrets in logs). CI runs it.
- **First-response target:** Default model + streaming so first token < 60s on normal connection; document.

**10 =** Install and run in one command; Docker; health check; first response < 1 min.

---

## 3. Speed of thinking (7 → 10)

**Gap:** Enforced latency budget; parallel/speculative where safe; optional cache; published numbers.

**Actions:**
- **Enforce budget:** If get_percentiles() exceeds targets (e.g. p95 > 15s), log warning or fail CI. Configurable targets.
- **Parallel/speculative:** Extend parallel execution to other safe multi-call flows (e.g. tool-choice + first chunk).
- **Response cache:** Optional cache by (system + user) hash with TTL; cache hits return in <50ms.
- **Publish:** Weekly or per-release latency report (p50/p95 ttft and ttc) in repo or CI artifact.

**10 =** Budget enforced; parallel where safe; optional cache; published "fastest" numbers.

---

## 4. Reasoning (structure) (7 → 10)

**Gap:** Measured on public reasoning benchmarks; auto hard-mode; optional formal check.

**Actions:**
- **Benchmark:** Run GSM8K/MATH or similar with Rain reasoning path; record and document scores.
- **Auto hard-mode:** When query matches heuristics (multi-step math, "prove", "step by step"), auto-enable deep reasoning.
- **Optional symbolic check:** For math, check numeric steps with sympy/numexpr; surface mismatches to model.
- **Structured steps:** Emit steps in JSON/markdown for scoring and verification.

**10 =** Measured on standard benchmarks; hard mode auto-triggers; optional formal check.

---

## 5. Creativity (structure) (8 → 10)

**Gap:** Human eval; "Rain wins" in at least one domain; creative API as product; diversity in CI.

**Actions:**
- **Human eval:** Blind A/B (Rain vs human/baseline) on 2–3 domains; define "win" (novelty + usefulness); run periodically.
- **"Rain wins" once:** Publish one domain where Rain matches or beats human in that eval.
- **Creative API:** Expose creative mode (e.g. POST /creative or `rain creative --domain=product_ideas`) as a product feature.
- **Diversity in CI:** In creativity eval, compute diversity; fail or warn if below threshold.

**10 =** Human eval on file; Rain wins in ≥1 domain; creative API is product; diversity in CI.

---

## 6. Memory (8 → 10)

**Gap:** No single point of failure; long-session compression; optional cross-session; tuning via config.

**Actions:**
- **Timeline as source of truth:** When vector disabled/fails, all experience in timeline; no feature assumes vector.
- **Long-horizon compression:** Optional summarization of older turns (e.g. every N turns) so context stays bounded.
- **Cross-session:** Optional user/session id for scoped persistence across restarts.
- **Tuning:** Expose RETRIEVAL_WEIGHTS and MIN_RETRIEVAL_SCORE via config.

**10 =** Memory never blocks; long sessions compressed; optional cross-session; configurable tuning.

---

## 7. Breadth (features) (8 → 10)

**Gap:** Task-type matrix; pluggable tools; one best-in-class vertical; multi-modal documented.

**Actions:**
- **Task matrix:** Doc: task type (QA, coding, planning, creativity, analysis) vs recommended Rain path.
- **Pluggable tools:** Clean register-tool API; doc + one example (e.g. custom search).
- **One vertical:** Pick one (e.g. research assistant or product ideation); make it exemplary (docs, preset).
- **Multi-modal:** Document "with voice" and "with vision" flows.

**10 =** Every task type has a path; tools pluggable; one vertical best-in-class; multi-modal documented.

---

## 8. Transparency / measurability (8 → 10)

**Gap:** Single scorecard; reproducible runs; changelog tied to metrics.

**Actions:**
- **Scorecard:** One doc or dashboard: capability, safety, speed, constraints. Update per release.
- **Reproducible:** Script(s) to run benchmarks from fixed seed/prompts; document how to reproduce.
- **Changelog:** Per release, note which metrics changed (e.g. latency p95 −10%).
- Optional: public leaderboard for same benchmarks.

**10 =** One scorecard; reproducible; changelog tied to metrics; optional public leaderboard.

---

## Suggested order

1. **Deployment** and **Transparency** first (run anywhere, see numbers).
2. **Safety** (path audit, red-team, constraint doc).
3. **Speed** (enforce budget, cache, parallel, publish).
4. **Reasoning** and **Creativity** (benchmarks, human eval, "Rain wins" once).
5. **Memory** and **Breadth** (robustness, compression, task matrix, one vertical).

When every dimension is 10, update the rating doc to reflect it.
