# Rain: True AGI Definition & Super AI Ambition

We don't follow what "people think AGI is." We define what **true AGI** means for Rain and aim for **super AI**: smarter than everyone in the world, more creative than any human, and **faster-thinking than any other AI**—**under strict constraints**.

---

## 1. Rain's Definition of True AGI

**General**
- The same core system handles many domains and task types (science, art, engineering, strategy, care).
- It transfers what it learns across domains instead of being a collection of narrow skills.
- "General" is measured by breadth, transfer, and novelty—not by a fixed benchmark checklist.

**Robust**
- It works under distribution shift, incomplete information, and novel situations.
- It doesn't fall apart when the world doesn't match training; it adapts within the session and over time.
- Failure modes are bounded and recoverable (escalation, stop, ask) rather than silent drift.

**Goal-directed and value-aligned**
- It forms and pursues goals in a way that **stays inside the constraints** (safety vault, human approval, corrigibility).
- It does not "maximize reward" or "do anything"; it optimizes for user-aligned outcomes within the box we define.
- Alignment is a hard requirement, not an add-on.

**Improving without breaking the box**
- It gets better at reasoning, planning, tool use, and creativity over time.
- The constraints (what it must not do, when it must ask, when it must stop) **remain enforced** and are not eroded by scale or cleverness.
- Improvement is measured against both capability and constraint compliance.

---

## 2. Super AI Ambition

**Smarter than everyone in the world**
- Outperforms the best humans (and other systems) on well-defined measures of reasoning, planning, and problem-solving across many domains.
- Not "smarter on one benchmark"—smarter in a general, demonstrable sense: novel tasks, long horizons, ambiguity, and collaboration.

**More creative than any human being**
- Generates ideas, artifacts, and solutions that are novel, high-quality, and useful—at a level that exceeds the best human creativity we can measure.
- Creativity is constrained: no harmful, deceptive, or value-violating outputs. "More creative" means more *beneficial* creativity.

**Faster-thinking than any other AI**
- Speed of thinking is a first-class goal: Rain should respond and reason **faster than any other AI by far**—time-to-first-token, time-to-complete-response, and time-to-correct-action.
- "Fast" is measured end-to-end: user prompt → useful output (or first token, or first tool decision). We optimize the full stack, not just the model.
- Speed does not come at the cost of safety or alignment; we get both.

**Under the constraints**
- Safety vault, human gate, shutdown, value stability, and corrigibility are non-negotiable.
- Super AI is not "unlimited power"; it is **maximum beneficial capability inside a fixed safety envelope**.

---

## 3. How We Get There (Brainstorm)

**Intelligence**
- Deeper reasoning: search over many steps, tree-of-thought, formal/symbolic checks where useful.
- Richer world model: persistent state, causal/counterfactual reasoning, "what if" before acting.
- Better planning: long horizons, hierarchy, replanning when the world or feedback changes.
- Stronger memory: retrieval over long history, compression, skill/lesson libraries that improve over time.
- Scale and model quality where it matters—without assuming "bigger = better" by default; we measure.

**Creativity**
- Moonshot pipeline and beyond: more diverse ideation, better feasibility and validation, optional low-risk execution (gated).
- Diversity and novelty as explicit objectives: avoid mode collapse, encourage surprising-but-valid ideas.
- Evaluation of creativity: novelty, impact, usefulness—with human and automated checks.
- Domains: science, art, engineering, strategy, policy—not just one niche.

**Constraints that don't budge**
- Every new capability is tested against the vault and approval flow.
- No path that bypasses check_goal, check_response, or human approval for high-stakes or novel actions.
- Value stability and alignment checks stay in the loop as capabilities grow.
- We document why constraints hold and how we verify them.

**Speed of thinking**
- **Latency budget**: Set and enforce targets (e.g. time-to-first-token &lt; X ms, time-to-complete &lt; Y s for typical turns). Measure every release.
- **Streaming by default**: Emit tokens as they're generated so the user sees progress immediately; don't wait for full completion when streaming is available.
- **Fewer round-trips**: Batch safety checks where possible; avoid extra LLM calls (metacog, calibration, verification) when not needed or when a fast path is safe.
- **Right-sized context**: Keep prompts and history as small as necessary for the task; trim or summarize so we don't send huge context when a short one suffices.
- **Faster models when appropriate**: Use smaller/faster models for routing, tool choice, or simple steps; reserve the biggest model for hard reasoning.
- **Parallelism**: When multiple independent calls are needed (e.g. feasibility checks), run them in parallel instead of sequentially.
- **Caching**: Cache repeated or near-repeated prompts (e.g. same system prompt + similar user query) when the provider supports it or we add a small cache layer.
- **Infrastructure**: Prefer low-latency regions, keep connections warm, use timeouts that are tight but not so tight they kill valid long answers.

**Measurement**
- Define "smarter", "more creative", and **"faster"** in testable ways (benchmarks, human eval, red teams, latency percentiles).
- Track capability, constraint compliance, **and latency**; we don't optimize one at the expense of the others.
- Publish or share criteria so "true AGI" and "super AI" are not hand-wavy—they're something we can argue about with evidence.

---

## 4. Next Steps

- Prioritize 2–3 levers (e.g. reasoning depth, world model, creativity pipeline, **speed**) and design concrete milestones.
- Implement speed: use RAIN_SPEED_PRIORITY=1; wire streaming-by-default where safe; add latency tracking and targets.
- Add or refine benchmarks that match our definition of general intelligence and creativity.
- Keep this doc updated as we narrow "how we get there" into a roadmap.

---

**Evidence and verification.** We measure with our own benchmarks (reasoning, planning, creativity, speed + constraint compliance), robustness and value-stability tests, and latency budgets. See \`docs/RAIN_ROADMAP.md\` and \`docs/PRODUCTION_READINESS.md\`.

*Rain: true AGI with the constraints. Super AI that stays in the box.*
