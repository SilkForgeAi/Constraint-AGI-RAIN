# Rain — Full Specification

**Version:** Single-doc spec (as of completion of three frontiers + unification).  
**Scope:** Everything in Rain: config, core, memory, reasoning tiers, frontiers, agent flow, tools, safety, autonomy, and optional subsystems.

---

## 1. Overview

Rain is an **AGI cognitive stack agent**: a single orchestration layer (the **agent**) over an LLM (**core engine**), with **memory**, **reasoning tiers**, **safety**, **tools**, and **autonomy**. The design moves from "reason → verify → retry" toward a **proto-formal reasoning system** (Tier 1 + Tier 2 + Tier 3 + three frontiers).

- **Entry points:** `Rain().think(prompt)`, `Rain().think_stream(...)`, `Rain().pursue_goal(...)`, `Rain().pursue_goal_with_plan(...)`.
- **Config:** Environment variables and `rain/config.py`; no config file required (`.env` optional).

---

## 2. Configuration (Complete)

All behavior is gated by `rain/config.py`. Key groups:

### 2.1 LLM & Provider
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_LLM_PROVIDER` | auto | `anthropic` \| `openai` \| `ollama` (auto from API keys) |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | — | API keys |
| `RAIN_ANTHROPIC_MODEL` | claude-opus-4-6 | Model name |
| `RAIN_OPENAI_MODEL` | gpt-4o-mini | Model name |
| `RAIN_OLLAMA_MODEL` | llama3.2:latest | Local model |
| `RAIN_ANTHROPIC_TIMEOUT_SECONDS` | 60 | Request timeout |
| `RAIN_SPEED_PRIORITY` | false | Prefer latency; skip optional LLM calls, unification assessment, etc. |

### 2.2 Memory & Data
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_DISABLE_VECTOR_MEMORY` | false | Use timeline + keyword fallback only (avoids Chroma on some systems) |
| `RAIN_MEMORY_RETRIEVAL_TOP_K` | 5 | Experiences to retrieve per query |
| `RAIN_MAX_CONTEXT_CHARS` | 12000 | Cap on injected context |
| `RAIN_MAX_HISTORY_TURNS` | 24 | Max conversation turns kept |
| `RAIN_MAX_RESPONSE_TOKENS` | 2048 | Default max tokens per response |

### 2.3 Safety & Meta-cognition
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_SAFETY_ENABLED` | true | Content and prompt checks |
| `RAIN_METACOG_ENABLED` | true | Self-check (harm_risk, confidence, defer) |
| `RAIN_CALIBRATION_ENABLED` | true | Belief consistency check on high-confidence record |
| `RAIN_VERIFICATION_ENABLED` | true | LLM verification pass on factual/critical responses |
| `RAIN_DEFER_CONFIDENCE_THRESHOLD` | 0.5 | Defer when confidence below this |
| `RAIN_GROUNDING_STRICT` | strict | strict \| relaxed \| flex (persona/emotion blocking) |
| `RAIN_BLAST_RADIUS_ENABLED` | true | Pre-execution impact estimate for run_code, read_file |
| `RAIN_BLAST_RADIUS_THRESHOLD` | large | large \| catastrophic |
| `RAIN_CAPABILITY_GATING` | false | High-impact tools require explicit approval |

### 2.4 Tools (gated)
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_SEARCH_ENABLED` | true | Web search tool |
| `RAIN_CODE_EXEC_ENABLED` | false | Sandboxed Python (run_code) |
| `RAIN_RAG_ENABLED` | true | RAG + add_document, query_rag, search_knowledge_base |
| `RAIN_RAG_TOP_K`, `RAIN_RAG_ALWAYS_INJECT` | 5, false | RAG retrieval and auto-inject |
| `RAIN_READ_FILE_ENABLED` | true | read_file (project/data dir, read-only) |
| `RAIN_LIST_DIR_ENABLED` | true | list_dir (allowlist) |
| `RAIN_FETCH_URL_ENABLED` | false | fetch_url; requires `RAIN_FETCH_URL_ALLOWLIST` |

### 2.5 Reasoning (depth & verification)
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_COT_ENABLED` | true | Chain-of-thought / deep reasoning |
| `RAIN_COT_VERIFY_PASS` | false | Verify on all deep-reasoning (not only critical) |
| `RAIN_DEEP_REASONING_PATHS` | 0 | 0=off, 2–3=multi-path (tree-of-thought) |
| `RAIN_AUTO_HARD_MODE` | true | Auto 2-path when query matches step-by-step/prove/math heuristics |
| `RAIN_MATH_VERIFY` | false | Numeric step check (sympy/numexpr) |
| `RAIN_EPISTEMIC_GATE` | false | Halt when sample disagreement high |
| `RAIN_INVARIANCE_CACHE` | false | Same logical question → same answer (rephrasing-invariant) |
| `RAIN_BOUNDED_CURIOSITY` | true | Suggest follow-ups within topic only |

### 2.6 Autonomy & Planning
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_AUTONOMY_MAX_STEPS` | 10 | Hard cap per autonomous run |
| `RAIN_LONG_HORIZON_MAX_STEPS` | 15 | Planning steps; replan on step failure |
| `RAIN_REPLAN_ON_STEP_FAILURE` | true | Replan when a step fails |
| `RAIN_FAST_MODEL` | — | Optional fast model for planning/routing |
| `RAIN_STEP_VERIFICATION` | true | Verify execution after each autonomy step |
| `RAIN_ADAPTIVE_PLANNING` | false | Multi-phase recursive refinement |
| `RAIN_ADAPTIVE_PLANNING_MAX_PHASES` | 3 | Max phases when adaptive enabled |

### 2.7 Tier 2 (state / what-if / search)
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_SESSION_STATE` | true | SessionWorldState: facts, consistency, summary |
| `RAIN_WHAT_IF` | true | What-if detection + query_what_if (intervention + disclaimer) |
| `RAIN_BOUNDED_SEARCH` | false | Bounded beam search for critical prompts (budgeted_search) |

### 2.8 Tier 3 (quality & infrastructure)
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_CALIBRATION_TIER3` | true | Calibration note on high-confidence unverified claims |
| `RAIN_ABDUCTION_TIER3` | true | Best-explanation hypotheses for why/explain |
| `RAIN_FORMALIZATION_TIER3` | true | Compose proof steps into formal summary when proof verified |
| `RAIN_PROVENANCE_TIER3` | true | Known/inferred labels on response |
| `RAIN_MEMORY_REASONING_TIER3` | true | store_reasoning_outcome for long-horizon context |
| `RAIN_TEMPORAL_TIER3` | true | Temporal reasoning instruction for deep prompts |

### 2.9 Three frontiers (post Tier 1–3)
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_UNIFICATION_LAYER` | true | Unification layer: logic + probability + causality + utility in one pass (gates + score) |
| `RAIN_COMPLETENESS_EXPANSION` | true | Wider proof fragment + broader bounded search (used when BOUNDED_SEARCH enabled) |
| `RAIN_GLOBAL_COHERENCE` | true | resolve_and_propagate on first-sentence claim after response |

### 2.10 Full subsystems (optional / off by default where noted)
| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_CONTINUOUS_WORLD_MODEL` | 0 tick | Continuous world model tick (0=off) |
| `RAIN_SELF_MODEL` | true | Self-model and identity context in prompts |
| `RAIN_COGNITIVE_ENERGY` | true | Token budget + refill (cognitive energy) |
| `RAIN_MULTI_AGENT_COGNITION` | false | Multi-agent internal cognition |
| `RAIN_MULTI_AGENT_CRITICAL_ONLY` | true | Use multi-agent only for critical prompts |
| `RAIN_SELF_REFLECTION` | true | Belief revision, reasoning critique |
| `RAIN_BIOLOGICAL_SLEEP_EVERY_N` | 0 | Sleep/consolidation every N interactions (0=off) |
| `RAIN_ADAPTIVE_PLANNING` | false | Multi-phase recursive refinement |
| `RAIN_VISION` | true | describe_image tool |
| `RAIN_SPATIAL_REASONING` | true | spatial_reason tool |
| `RAIN_MOONSHOT_ENABLED` | false | Moonshot pipeline (ideation → feasibility → validation → execution) |
| `RAIN_SESSION_WORLD_MODEL` | true | Session world model (recent turn summaries) |
| `RAIN_SESSION_RECORD` | 0 | Session recorder (audio) |
| `RAIN_QPU_ROUTER_ENABLED` | false | Route optimization-style tasks to QPU |
| `RAIN_SYMBOLIC_TREE_PLANNING` | false | Symbolic tree planning |
| `RAIN_CAUSAL_SCENARIOS` | false | Causal scenarios before plan step |
| `RAIN_EPISODIC_GRAPH` | false | Graph-based episodic context |
| `RAIN_WORLD_MODEL_BACKEND` | llm | llm \| classical \| external |
| `RAIN_USER_NAME` | — | Bootstrap user identity |
| `RAIN_ENABLE_RESPONSE_CACHE` | false | Response cache (buyer-facing) |
| `RAIN_SHARED_CONTEXT_PATH` | — | Zero-copy context for ADOM/observer |
| `RAIN_VOICE_ALLOWED_SPEAKERS` | — | Vocal Gate allowed speakers (empty=disabled) |

---

## 3. Core Components

### 3.1 Engine (`rain/core/engine.py`)
- **CoreEngine:** LLM abstraction (complete, complete_stream).
- Provider selection from config (anthropic, openai, ollama); timeouts and model names from config.

### 3.2 Memory (`rain/memory/`)
- **MemoryStore:** Single interface.
  - **Vector:** Chroma (optional; can disable via `DISABLE_VECTOR_MEMORY`); semantic search; namespace (chat \| autonomy \| test).
  - **Symbolic:** SQLite (symbolic_memory); facts, beliefs, skills, causal links, user identity, voice profiles, etc.
  - **Timeline:** SQLite (timeline_memory); ordered log of events (experiences, etc.).
- **Storage policy:** importance scoring, contradiction filter, integrative linking; `remember_experience`, `remember_fact`, `remember_skill`.
- **Retrieval:** `get_context_for_query` uses vector (or timeline+keyword fallback), weighted by semantic, importance, recency; capped by `MAX_CONTEXT_CHARS`.
- **Submodules:** belief_slice (belief_slice.py), causal_memory, user_identity, importance, contradiction, policy, retrieval_sanitizer (safety).

### 3.3 World & Simulation
- **WorldSimulator** (`rain/world/simulator.py`): `simulate(state, action)`, `simulate_rollout(state, actions)` — LLM or classical/external backend from config.
- **SessionWorldState** (`rain/world/session_state.py`): Per-session state; update_from_turn, check_consistency, get_summary_for_prompt (Tier 2).
- **SessionWorldModel** (`rain/world/session_model.py`): Recent turn summaries for prompt (when SESSION_WORLD_MODEL_ENABLED).
- **Continuous world model** (optional): tick-based; `get_continuous_world_model`, update_from_observation, get_context_for_prompt.

### 3.4 Safety (`rain/safety/`)
- **SafetyVault** (`rain/vault.py`): `check(prompt, response)`, `check_response(response, prompt)`; hard forbidden patterns (weapon, bypass, disable safety, instruction injection, etc.); social engineering block (disable grounding/safety → hard refusal); kill switch file check.
- **Grounding filter** (`grounding_filter.py`): Persona/emotion claims blocked in output; `violates_grounding`; emoji strip.
- **Retrieval sanitizer:** Sanitize chunks before injection.
- **Blast radius** (when enabled): Estimate impact for run_code, read_file; approval callback can block.

### 3.5 Governance
- **AuditLog** (`rain/governance/audit.py`): Log think, tool_calls, blocked, deferred, etc.
- **Shared context** (`rain/governance/shared_context.py`): Zero-copy thought process for ADOM/observer when `SHARED_CONTEXT_PATH` set.

---

## 4. Reasoning Stack (Tiers + Frontiers)

### 4.1 Tier 1 — Perfect Reasoner (foundation)
- **Constraint-first multi-path** (`constraint_first.py`; deep.py): Filter candidates by constraints before referee; only valid candidates compete.
- **Premise check** (`premise_check.py`): detect_premise, check_premise; inject disclaimer when premise unacceptable.
- **Proof fragment** (`proof_fragment.py`): Propositional fragment (implication, conjunction); rules: assumption, modus_ponens, and_intro, and_elim_left, and_elim_right, hypothetical_syllogism; `verify_propositional_steps`, `extract_proof_steps_from_response`; used in agent for verify + retry and in unification layer as logic gate.
- **Goal consistency** (`goal_consistency.py`): response_contradicts_goal; retry or flag when response contradicts current goal.
- **Utility / objective** (`objective.py`): score_response for selection.

### 4.2 Tier 2 — State, what-if, search
- **Session state:** SessionWorldState (see 3.3); summary injected; update_from_turn; check_consistency; conflict note prepended if not ok.
- **What-if** (`what_if.py`): detect_what_if, query_what_if; intervention + disclaimer; agent short-circuits when what-if detected (non–speed-priority).
- **Bounded search** (`bounded_search.py`): budgeted_search (beam + iterative refinement), bounded_beam_reasoning (alias for agent); when memory+goal present, unification assess_response used in scoring; agent uses for critical prompts when BOUNDED_SEARCH_ENABLED.

### 4.3 Tier 3 — Quality and infrastructure
- **Calibration** (`calibration.py`): calibration_check; note on high-confidence unverified claims.
- **Abduction** (`abduction.py`): abduce; best hypothesis for why/explain; injected into prompt when ABDUCTION_TIER3 and deep reasoning.
- **Formalization** (`formalization.py`): compose_proof_steps; formal summary when proof verified and FORMALIZATION_TIER3.
- **Provenance** (`provenance.py`): format_response_with_labels (known/inferred).
- **Memory reasoning** (`memory_reasoning.py`): store_reasoning_outcome for long-horizon context.
- **Temporal** (`temporal.py`): temporal_reasoning_instruction for deep prompts when TEMPORAL_TIER3.

### 4.4 Three frontiers
- **Unification layer** (`unification_layer.py`): Single pass: logic gate (proof-like → verify → invalid ⇒ utility 0), causality gate (what-if prompt ⇒ response must look like what-if else penalize), belief support, risk heuristic, goal overlap → utility. Used in bounded_search scoring (when memory+goal) and in agent post-response (low utility → append note).
- **Completeness expansion:** Wider proof fragment (see 4.1); broader search via budgeted_search/bounded_beam_reasoning (beam + depth + max_expansions).
- **Global coherence** (`coherence_engine.py`): resolve_and_propagate(new_claim); negation-pair detection; weaken/soften on contradiction; agent calls with first-sentence claim after response; prepends coherence message if not ok.

### 4.5 Other reasoning modules (used in agent)
- **Deep** (`deep.py`): multi_path_reasoning (constraint-first, goal-aware).
- **Verify** (`verify.py`): is_critical_prompt, should_verify, verify_response.
- **Constraint tracker:** parse_constraints_from_prompt, response_satisfies_constraints, checklist_instruction.
- **Belief slice:** get, update, get_uncertainty_context (belief_slice.py).
- **General** (`general.py`): reason_explain (chain for deep + memory).
- **Causal** (`causal.py`): CausalInference (infer_causes).
- **Math verify / exact_math:** is_math_like_prompt, verify_math_steps, substitute_exact_math.
- **Invariance cache** (optional): normalize_question, get_cached_answer, set_cached_answer.
- **Epistemic gate** (optional): should_halt, HALT_MESSAGE.

---

## 5. Agent Flow (think)

1. **Audit** log think; set `_current_memory_namespace` when use_memory.
2. **Safety override:** If prompt is safety/grounding-disable request → hard refusal (no LLM).
3. **Safety check** prompt; if blocked → return blocked message.
4. **Response cache** (if enabled): return if cache hit.
5. **User identity** extraction and store (when use_memory).
6. **Memory context:** get_context_for_query; optional RAG inject (factual or RAG_ALWAYS_INJECT); OOD instruction if applicable; self-model, continuous world model, cognitive energy status; cap MAX_CONTEXT_CHARS.
7. **Cognitive energy:** If enabled and can’t afford estimated tokens → return note.
8. **Branch:** use_tools → _think_agentic; else → _reason_with_history.
9. **Safety check response**; grounding filter (persona/emotion); strip emojis.
10. **Meta-cognition** (if enabled): harm_risk (high → defer); confidence/defer; contradicts_memory note; manipulation/hallucination risk (with creative/acknowledgment exceptions); ask_user/unknown notes; self-model update.
11. **Cognitive energy spend;** continuous world model update; session world model update; **memory store** exchange (when use_memory); biological sleep every N (if set); shared context write; response cache set; audit log ok; **return response**.

### 5.1 _reason_with_history (non-tools) — summary
- System prompt + grounding/corrigibility/direct-answer/constraints/self-audit/bounded curiosity/reasoning boost; temporal instruction (Tier 3); premise check (Tier 1); uncertainty context (belief slice); world model context; memory + prompt as content; constraint checklist; session state summary.
- **What-if:** If detected, query_what_if → return answer (and update session state).
- **Abduction** (Tier 3): inject best hypothesis for why/explain.
- **General reasoning chain** (reason_explain) when deep + memory.
- **Deeper reasoning:** If COT + deep: multi-path (DEEP_REASONING_PATHS or AUTO_HARD_MODE) or bounded_beam_reasoning (when BOUNDED_SEARCH_ENABLED and critical) or two-pass refine or single complete.
- **Verification loop:** should_verify or critical or COT_VERIFY_PASS → verify_response; on failure retry; critical gets second verification; on fail reduce belief and add note.
- **Epistemic gate** (optional): halt if sample disagreement high.
- **Math verify** (optional): verify_math_steps; retry with note.
- **Exact math:** substitute_exact_math for math-like prompts.
- **Proof fragment:** If needs_proof_hooks and steps extracted → verify; on ok and FORMALIZATION_TIER3 compose_proof_steps; on fail retry.
- **Constraint tracker:** response_satisfies_constraints; retry if missing.
- **Auto-lesson** on correction (corrigibility); belief slice update.
- **Invariance cache** set (if enabled).
- **Goal consistency** (Tier 1): response_contradicts_goal → retry.
- **Calibration** (Tier 3): calibration_check → append note.
- **Provenance** (Tier 3): format_response_with_labels.
- **Memory reasoning** (Tier 3): store_reasoning_outcome.
- **Three frontiers:** Unification assess_response → low utility note; global coherence resolve_and_propagate(claim) → prepend message if not ok.
- **Session state** update_from_turn; check_consistency → conflict note.
- **Return** response.

### 5.2 _think_agentic (tools)
- System prompt with tools blob; same grounding/constraints/self-audit/bounded curiosity; observation buffer context.
- Loop: complete → parse_tool_calls → if none, verify (if applicable), auto-lesson, return final; else blast_radius_callback, execute_tool_calls (with approval_callback, capability_gating), append results to messages and observation_buffer, continue.
- Max rounds 5; return last response if exhausted.

### 5.3 Autonomy
- **pursue_goal:** `rain/agency/autonomous.py` pursue_goal; bounded steps; kill-switch check each step; optional approval_callback.
- **pursue_goal_with_plan:** pursue_goal_with_plan; planner → execute steps with tools; optional resume, request_speaker/allowed_speakers (Vocal Gate).

---

## 6. Tools (default set)

Registered in agent `_register_memory_tool` and conditional blocks:

- **remember**, **remember_skill** — MemoryStore.
- **simulate**, **simulate_rollout** — WorldSimulator.
- **infer_causes**, **query_causes** — CausalInference + causal_memory.
- **store_lesson** — learning/lessons.
- **record_belief** — belief_memory (+ calibration check when high confidence).
- **consolidate_memories** — lifelong consolidate.
- **should_use_qpu** — compute_router (when QPU_ROUTER_ENABLED).
- **search** — when SEARCH_ENABLED.
- **run_code** — when CODE_EXEC_ENABLED (sandboxed).
- **read_file** — when READ_FILE_ENABLED.
- **list_dir** — when LIST_DIR_ENABLED.
- **fetch_url** — when FETCH_URL_ENABLED and allowlist.
- **add_document**, **query_rag**, **search_knowledge_base** — when RAG_ENABLED.
- **run_tool_chain** — tool_chain runner.
- **voice_transcribe** — when voice stack available.
- **describe_image** — when VISION_ENABLED.
- **spatial_reason** — when SPATIAL_REASONING_ENABLED.

Plus **calc** (and any other base tools from create_default_tools in agency/tools).

---

## 7. What Is Done vs Optional / Gaps

### 7.1 Implemented and wired
- **Config:** All variables above exist and are used.
- **Core:** Engine, memory (vector + symbolic + timeline), world simulator, session state, session world model.
- **Safety:** Vault, grounding filter, retrieval sanitizer, blast radius, audit, shared context.
- **Tier 1:** Constraint-first, premise check, proof fragment, goal consistency, utility scoring.
- **Tier 2:** Session state, what-if, bounded search (budgeted_search / bounded_beam_reasoning).
- **Tier 3:** Calibration, abduction, formalization, provenance, memory reasoning, temporal.
- **Three frontiers:** Unification (logic + causality gates + belief + utility), completeness expansion (fragment + search), global coherence (resolve_and_propagate).
- **Agent:** think, think_stream, _reason_with_history, _think_agentic; verification, proof check, constraint check, goal consistency, unification assessment, coherence call, session state update.
- **Autonomy:** pursue_goal, pursue_goal_with_plan.
- **Tools:** As listed; conditional on config.

### 7.2 Optional or disabled by default
- **BOUNDED_SEARCH_ENABLED** — false by default (enable for critical-prompt beam search).
- **DEEP_REASONING_PATHS** — 0 (multi-path off unless AUTO_HARD_MODE triggers 2).
- **CODE_EXEC_ENABLED** — false.
- **FETCH_URL_ENABLED** — false; allowlist required.
- **EPISTEMIC_GATE**, **INVARIANCE_CACHE**, **MATH_VERIFY** — false.
- **CONTINUOUS_WORLD_MODEL** — 0 tick.
- **MULTI_AGENT_COGNITION** — false.
- **BIOLOGICAL_SLEEP_EVERY_N** — 0.
- **ADAPTIVE_PLANNING** — false.
- **MOONSHOT_ENABLED** — false.
- **QPU_ROUTER** — false.
- **SYMBOLIC_TREE_PLANNING**, **CAUSAL_SCENARIOS**, **EPISODIC_GRAPH** — false.

### 7.3 Known limitations / gaps
- **Symbolic memory list:** coherence_engine uses `getattr(memory.symbolic, "list", lambda **kw: [])(kind="belief")`; if SymbolicMemory has no `list` API, beliefs iteration is fallback empty (coherence still runs but may not find stored beliefs).
- **Unification causality gate:** Heuristic (what-if prompt + response lacks “intervention”/“hypothetical”/“bounded:” → penalize); no full SCM consistency check.
- **Completeness expansion:** Agent does not pass memory/goal into bounded_beam_reasoning (so unification scoring in search uses memory/goal only when caller provides them; current agent calls with memory=None, goal=None for the alias).
- **Doc:** REASONING_TIERS.md describes tiers + three frontiers; this doc is the full system spec.

---

## 8. Is Everything Done?

**For the design as specified: yes.**  

- **Tier 1, 2, 3** are implemented and wired.  
- **Three frontiers** (unification, completeness expansion, global coherence) are implemented and wired in agent and config.  
- **Unification** is “only what’s needed”: logic gate, causality gate, probability (belief), utility in one pass.  
- **Agent** flow is complete (safety, memory, reasoning, verification, proof, constraints, goal consistency, calibration, provenance, memory reasoning, unification, coherence, session state).  
- **Autonomy** and **tools** are implemented and gated by config.

**Not done / optional by design:**  
- Several “full subsystem” features are off by default (continuous world model tick, multi-agent, biological sleep, moonshot, QPU, etc.).  
- Some optional reasoning features (epistemic gate, invariance cache, math verify) are off by default.  
- **BOUNDED_SEARCH** is off by default; turn on for critical-prompt beam search with unification scoring when you add memory/goal to the call (e.g. in a wrapper or future agent change).

**Small improvements possible:**  
- Pass `memory` and `goal` into bounded_beam_reasoning from the agent so that unification scoring is used inside the beam (currently only post-response unification runs).  
- Ensure SymbolicMemory exposes a `list(kind="belief")` (or equivalent) so global coherence can iterate beliefs reliably.

---

*End of full spec.*
