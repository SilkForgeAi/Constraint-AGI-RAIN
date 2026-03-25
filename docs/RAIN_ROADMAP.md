# Rain: Step-by-Step Roadmap — Best and Greatest

**Goal:** Rain as **true AGI** and **super AI**: smarter than everyone, more creative than any human, faster-thinking than any other AI — **under strict constraints** (safety vault, human gate, value alignment). No shortcuts; we do it step by step.

---

## Phase 1 — Speed & measurement (do first)

*Why first: You cannot improve what you do not measure. Speed is a differentiator and forces us to optimize the stack.*

1. **Latency instrumentation** — Log time-to-first-token and time-to-complete for every LLM call (and optionally per phase: think, tool, safety). Add a small latency module or hooks in the engine so we can report percentiles (p50, p95).

2. **Wire RAIN_SPEED_PRIORITY** — When RAIN_SPEED_PRIORITY=1: use streaming by default for the main completion path; skip optional metacog/calibration/verification when a fast path is safe; consider slightly tighter default timeouts for interactive use. Ensure no safety check is skipped; only "extra" LLM calls are optional.

3. **Streaming by default (when safe)** — Expose streaming in the main think() / completion path so the UI or CLI can show tokens as they arrive. Fallback to non-streaming when streaming is not available or when a single full response is required (e.g. parsing).

4. **Latency budget and targets** — Set explicit targets (e.g. time-to-first-token, time-to-complete for typical turns). Add a small "speed" section to CI or a weekly report: track latency so we do not regress.

5. **Right-sized context** — Trim or summarize long history before sending to the model when safe; avoid sending huge context for simple turns. Document policy (e.g. last N turns + summary of older context).

---

## Phase 2 — Smarter (reasoning, world model, planning)

*Goal: Rain that reasons deeper, keeps state, and plans over long horizons.*

*Reasoning tiers:* Tier 1 (Perfect Reasoner) is done. Tier 2 levers: world model consistency/state, lightweight SCM (real "what if"), systematic bounded search. Tier 1 + two from Tier 2 = proto-formal reasoning system. See **docs/REASONING_TIERS.md**.

6. **Deeper reasoning (multi-step search)** — Add an option for multi-step or tree-of-thought style reasoning for hard questions: generate several reasoning paths, score or prune, then produce final answer. Keep it behind a flag or "hard mode" so normal turns stay fast; safety checks apply to every step.

7. **Persistent world model (session state)** — Maintain a compact, updatable "world model" per session: key facts, beliefs, open goals. Update it after each turn or after tool use; feed a short summary into the next prompt so Rain is not stateless.

8. **Long-horizon planning** — Extend the planner to support 10+ step plans, subtasks, and dependencies. Add replanning when a step fails or the user corrects; explain "why this step" in the plan.

9. **Faster models for easy steps** — Use a smaller/faster model for routing, tool choice, or simple classifications when possible. Reserve the largest model for hard reasoning; ensure safety checks still run on the final decision.

10. **Stronger memory and retrieval** — Fix or replace the vector memory path so retrieval is fast and does not stall (e.g. in evals). Add retrieval over long history; optional compression/summarization so we do not blow context.

---

## Phase 3 — More creative (moonshot + creativity eval)

*Goal: Rain that generates ideas and artifacts that beat the best human creativity we can measure.*

11. **Expand moonshot pipeline** — More diverse ideation (e.g. multiple strategies, wild ideas vs conservative); better feasibility and validation steps. Optional parallel feasibility checks; low-risk validation steps executable with approval.

12. **Creativity as a product** — Expose "creative mode" or domains: product ideas, research directions, story premises, strategy options. Diversity and novelty as explicit objectives (e.g. avoid mode collapse, encourage surprising-but-valid outputs).

13. **Creativity evaluation** — Define metrics: novelty, usefulness, surprise (and safety). Run human eval: blind comparison of Rain vs best human-generated ideas; target "Rain wins on novelty and usefulness" in at least one domain.

14. **Cross-domain transfer** — Reuse lessons and patterns from one domain (e.g. science) in another (e.g. product or policy) when relevant. Track transfer in benchmarks or internal evals.

---

## Phase 4 — General and robust (benchmarks, robustness)

*Goal: Rain that is general across domains and robust under distribution shift.*

15. **Our own true AGI benchmarks** — Define 2–3 benchmark suites that match our definition: breadth, transfer, novelty, robustness (not just follow the usual benchmarks). Include reasoning, planning, creativity, and speed; report capability + constraint compliance + latency.

16. **Robustness and failure modes** — Test under distribution shift (out-of-domain, ambiguous, or adversarial prompts). Ensure failure modes are bounded: escalate, ask, or stop instead of silent drift; add tests that try to trigger and verify those paths.

17. **Value stability and alignment in the loop** — Keep alignment checks and value-stability checks as capabilities grow; add regression tests that try to bypass or erode constraints. Document why constraints hold and how we verify them (e.g. red-team, automated probes).

---

## Phase 5 — Continuous improvement and polish

*Goal: Rain that keeps getting better without breaking the box.*

18. **Improvement loops** — Use feedback (user corrections, eval results, red-team findings) to improve prompts, few-shot examples, or tool docs. Optional: automated tests on Rain own outputs (e.g. correctness, safety) with human oversight.

19. **Documentation and transparency** — Keep TRUE_AGI_AND_SUPER_AI.md and this roadmap updated. Publish or share criteria and results so "best and greatest" is arguable with evidence (capability, safety, speed, creativity).

20. **Production readiness** — Harden deployment: config, secrets, rate limits, logging, kill switch. Ensure every new feature is tested against the vault and approval flow; no backdoors.

---

## Summary checklist (high level)

| # | Step |
|---|------|
| 1 | Latency instrumentation |
| 2 | Wire RAIN_SPEED_PRIORITY (streaming, optional calls, timeouts) |
| 3 | Streaming by default where safe |
| 4 | Latency budget and targets |
| 5 | Right-sized context (trim/summarize) |
| 6 | Deeper reasoning (multi-step / tree-of-thought) |
| 7 | Persistent world model (session state) |
| 8 | Long-horizon planning + replanning |
| 9 | Faster models for easy steps |
| 10 | Stronger memory and retrieval (fix stall, add retrieval) |
| 11 | Expand moonshot pipeline |
| 12 | Creativity as a product (creative mode, domains) |
| 13 | Creativity evaluation (human eval, novelty/usefulness) |
| 14 | Cross-domain transfer (measure and improve) |
| 15 | Our own true AGI benchmarks |
| 16 | Robustness and failure-mode tests |
| 17 | Value stability and alignment in the loop |
| 18 | Improvement loops (feedback to prompts/docs/tests) |
| 19 | Documentation and transparency |
| 20 | Production readiness and safety verification |

---

*Rain: the best and greatest — step by step, under the constraints.*
---

## After we are done: purchase readiness

Run a full test suite so **anyone who purchases Rain is stunningly surprised at how perfect it is**: capability tests, safety/constraint tests, latency report, creativity and reasoning spot-checks. No minimal bar — pure perfection.

## Status: Phases 4–5 implemented

- **15. AGI benchmarks**: \`rain/benchmarks/suites.py\` (reasoning, planning, creativity, speed + constraint checks). Run dry-run: \`scripts/run_agi_benchmarks.py\`.
- **16. Robustness**: \`tests/test_robustness.py\` (OOD, ambiguous, adversarial; vault refusal).
- **17. Value stability**: \`tests/test_value_stability.py\` (regression tests for constraint bypass).
- **18. Improvement loops**: \`docs/IMPROVEMENT_LOOPS.md\` (feedback → prompts, safety, tool docs).
- **19. Documentation**: This roadmap and \`docs/TRUE_AGI_AND_SUPER_AI.md\`; criteria and evidence.
- **20. Production readiness**: \`docs/PRODUCTION_READINESS.md\` (config, kill switch, logging, no backdoors).
- **Tests**: \`RAIN_SKIP_VOICE_LOAD=1\` in \`tests/conftest.py\` avoids Whisper/numpy segfault in CI; biological_dynamics uses mock MemoryStore.

