# Reasoning Tiers — From Heuristic to Proto-Formal

Rain's reasoning stack is structured in tiers. Tier 1 is the foundation; Tier 2 is the next levers; Tier 3 is the last tier: quality and infrastructure. Together they move Rain from "reason → verify → retry" toward a **proto-formal reasoning system**.

---

## Tier 1 — Perfect Reasoner (foundation) ✅

*Status: Implemented.*

- **Constraint-first multi-path** — Filter candidates by constraints before referee; only valid candidates compete.
- **Premise check** — Detect and validate assumptions (assume/suppose/given); inject disclaimer when premise is unacceptable.
- **Scoped formal soundness** — Propositional proof fragment + verifier; when response looks like a proof, verify steps and retry on failure.
- **Explicit utility + goal consistency** — Score responses by utility (including goal alignment); before return, check that response does not contradict current goal; retry or flag if it does.

*Code:* rain/reasoning/constraint_first.py, premise_check.py, proof_fragment.py, goal_consistency.py, objective.py; deep.py (constraints, goal); agent.py (all wired).

---

## Tier 2 — After Tier 1 (next levers) ✅

*Status: Implemented.*

*Goal: Persistent state, real "what if", and bounded completeness. These change what the system can guarantee.*

1. **World model (consistency/state)**  
   Maintain and enforce consistent world state (or session state) that reasoning and plans can read and update. Use it to avoid contradictory beliefs and to ground "what is true here" across turns.

2. **Lightweight SCM (real "what if")**  
   Structural causal model or causal layer that supports genuine counterfactual / interventional "what if" queries. Beyond correlation or scenario listing: explicit interventions and (where possible) bounded causal conclusions.

3. **Systematic search (bounded completeness)**  
   Bounded search over reasoning or plan space (e.g. beam, branch-and-bound, or explicit exploration limits). Ensures "we looked here" within a defined envelope rather than a single path.

*Code:* rain/world/session_state.py (SessionWorldState); rain/reasoning/what_if.py (detect_what_if, query_what_if); rain/reasoning/bounded_search.py (bounded_beam_reasoning). Agent: SESSION_STATE_TIER2, WHAT_IF_ENABLED, BOUNDED_SEARCH_ENABLED; session summary in prompt, what-if short-circuit, bounded beam for critical prompts.

*Proto-formal milestone:* **Tier 1 plus any two from Tier 2** (e.g. world model + SCM, or world model + search) puts Rain in a different category from standard "reason → verify → retry" wrappers: validity filtering, premise validation, a proof fragment, and utility-based selection, plus either **persistent state**, or **simulation/what-if**, or **search**. That is not AGI but it is a **distinct class of system** — a proto-formal reasoning system.

---

## Tier 3 — Quality and infrastructure (last tier) ✅

*Status: Implemented.*

*Goal: Trust, interpretability, and coverage. They improve the system but do not by themselves change the system class. Correct to put after Tier 1–2.*

- **Calibration** — Confidence and uncertainty aligned with actual correctness.
- **Abduction** — Best-explanation reasoning; hypothesis formation and selection.
- **Compositional formalization** — Larger or more structured formal fragments (e.g. composed proof steps, domain schemas).
- **Known/inferred labels** — Explicit tagging of what is known vs inferred; provenance for claims.
- **Memory** — Long-horizon and cross-session context; retrieval and consolidation.
- **Temporal** — Time-aware state and reasoning; ordering, persistence, and "when" labels.

These levers improve trust, interpretability, and coverage on top of the Tier 1–2 foundation.

*Code:* rain/reasoning/calibration.py, abduction.py, formalization.py, provenance.py, temporal.py, memory_reasoning.py. Agent: CALIBRATION_TIER3, ABDUCTION_TIER3, FORMALIZATION_TIER3, PROVENANCE_TIER3, MEMORY_REASONING_TIER3, TEMPORAL_TIER3; temporal instruction, abduction hypothesis inject, proof compose, calibration note, provenance prefix, store_reasoning_outcome.

---

## Three frontiers (post Tier 1–3)

*Status: Implemented.*

Three extensions that sit on top of the tier stack: **unification**, **completeness expansion**, and **global coherence**.

1. **Unification layer** — Logic + probability + causality + utility in one structured pass. Used in bounded search scoring (when memory/goal are present) and in post-response assessment. Low-utility responses for the current goal get an optional note.  
   *Code:* `rain/reasoning/unification_layer.py` (`assess_response`, `UnifiedAssessment`). Agent: `UNIFICATION_LAYER_ENABLED`; post-response assessment when not in speed priority.

2. **Completeness expansion** — Wider decidable proof fragment and broader (but still bounded) search. Proof fragment adds rules: `and_intro`, `and_elim_left`, `and_elim_right`, `hypothetical_syllogism`; operators: implication, conjunction. Search uses `budgeted_search` with beam + iterative refinement; `bounded_beam_reasoning` is the alias used by the agent.  
   *Code:* `rain/reasoning/proof_fragment.py` (verifier + extractor), `rain/reasoning/bounded_search.py` (`budgeted_search`, `bounded_beam_reasoning`). Agent: `BOUNDED_SEARCH_ENABLED` (and optionally `COMPLETENESS_EXPANSION_ENABLED` for future toggles).

3. **Global coherence engine** — Contradiction resolution and bounded belief propagation. When a new claim is stored, beliefs are checked for negation pairs; contradictions trigger weaken or soften; otherwise the new claim is reinforced.  
   *Code:* `rain/reasoning/coherence_engine.py` (`resolve_and_propagate`, `CoherenceResult`). Agent: `GLOBAL_COHERENCE_ENABLED`; invoked with first-sentence claim after each response; coherence message prepended if not ok.

Config: `rain/config.py` — `UNIFICATION_LAYER_ENABLED`, `COMPLETENESS_EXPANSION_ENABLED`, `GLOBAL_COHERENCE_ENABLED` (env: `RAIN_UNIFICATION_LAYER`, `RAIN_COMPLETENESS_EXPANSION`, `RAIN_GLOBAL_COHERENCE`; default on).

---

## Summary

| Tier   | Role                         | Examples                                                                 |
|--------|------------------------------|--------------------------------------------------------------------------|
| **1**  | Foundation (done)            | Constraint-first, premise check, proof fragment, utility + goal consistency |
| **2**  | Next levers (state/what-if/search) | World model consistency/state, lightweight SCM, systematic bounded search   |
| **3**  | Quality and infrastructure (last) | Calibration, abduction, compositional formalization, known/inferred, memory, temporal |

**Proto-formal reasoning system:** Tier 1 ✅ + two from Tier 2 → distinct system class beyond "reason → verify → retry".
