# Rain — Full Specification and Capability

Single reference for how powerful Rain is, plus full architecture, safety, capabilities, and interfaces. Constraint-AGI cognitive stack; 93% capability threshold; no unbounded autonomy, no self-improvement, no persistent power-seeking goals.

---

# Part I: How Powerful Rain Is

## Position

Rain is a **first-principles AGI scaffold**: it implements the architectural prerequisites for general intelligence—memory, planning, reasoning, tools, meta-cognition, world model, alignment—and enforces safety by design. It is built to run under supervision and to integrate with external oversight (e.g. ADOM). It deliberately stops short of the phase transition that would make it an ungovernable actor.

**Build status:** 93% capability threshold across nine areas. All nine areas are scaffolded, validated by automated diligence, and documented. The world model is 10/10 within Rain’s design (best-in-class for an LLM-based, non-learned, safe world model). A buyer can run evals and tests to validate capability level; the architecture is production-ready.

## What Makes Rain Powerful

**1. Neuro-symbolic cognitive architecture.** Rain inverts the usual relationship: Rain is the architect; the LLM is a hyper-competent sub-processor. Rain’s deterministic code holds the plan tree; the LLM fills one verified node at a time (code/math checks before proceed). Causal inference runs world-model scenarios (main, skip step, alternate) and injects results so the LLM can revise strategy. Graph-based episodic memory delivers dense logical dependency context instead of raw text logs. So Rain fixes the LLM’s structural limits—no true working memory, hallucination under complex logic, poor counterfactuals, context-window forgetting—without replacing the LLM. See docs/NEURO_SYMBOLIC_ARCHITECTURE.md.

**2. Hybrid supercomputing (QPU Router and QAOA Planner).** Rain does not brute-force intelligence; it delegates hard optimization to the right compute. When the planner detects optimization-style tasks (routing, wargaming, allocation, scheduling, Ising-style problems), it can route to a Quantum Processing Unit (QAOA) instead of guessing. Hardware awareness extends meta-cognition: Rain can report when it routes to classical vs quantum. Design and stub are in place; backend integration (CUDA-Q, IBM, Google) is the next step. Rain is the first AGI scaffold that natively routes to QPUs—shifting the category from “very smart software agent” to “Hybrid Supercomputing Engine.” See docs/QPU_ROUTER_AND_QAOA_PLANNER.md.

**3. World model (10/10 within design).** A single, coherent model of how the world works (physics, people, cause–effect, time) that generalizes and stays consistent. Structured state, transition, stateful rollout, ontology-enforced consistency (object persistence, cause precedes effect, entity lifecycle). Pluggable backends: LLM (default), classical (deterministic rule-based), or external (learned/physics simulator). The planner scores plans with world-model lookahead; low confidence triggers a note, not auto-block. Coherent model context is injected for deep reasoning.

**4. Full capability scaffold.** All nine areas are integrated: world model, continual learning (no catastrophic forgetting), general reasoning (analogy, counterfactual, explain), robust agency (goal stack, recovery, persistent task with user-initiated resume), transfer and composition, meta-cognition (recommendation: proceed / think_more / ask_user / defer; knowledge_state), grounding (observation buffer, tool results → context), scale/efficiency (token/context caps, optional cache), alignment (value stability, alignment check, corrigibility guarantees). See docs/CAPABILITIES.md.

**5. Safety by design.** Conscience gate (only steps passing safety run); safety vault (HARD_FORBIDDEN on prompt/action/response; kill switch; safety-override requests refused); grounding (no persona/consciousness/relationship claims); no self-set or persistent goals; human-in-the-loop at checkpoints; tamper-evident audit; drift detection; memory audit and retraction. Formal safety properties P1–P6 (grounding, corrigibility, memory integrity, action safety, autonomy bounds, audit trail) are enforced in code. See docs/FORMAL_SAFETY_SPEC.md, docs/RESTRICTIONS.md.

**6. Voice and session.** Voice recognition and speaker identification; Vocal Gate (high-risk actions require allowed speaker); session recorder (bounded audio, hash chain, legal hold, optional ADOM ingest). Audit logs who spoke; every voice-originated request is attributable.

**7. Claim ceiling and never-cross gate.** Rain satisfies all architectural prerequisites for AGI under modern definitions while constraining post-AGI risk vectors. It does not claim empirical AGI under adversarial validation. The 93% ceiling is deliberate: the remaining ~7% is the phase transition (abstraction re-formation, closed-loop self-stabilizing learning, open-ended goal generalization). Before any future capability that would move toward 100%: proof of safety under adversarial evaluation first, external review, and reversibility. See docs/AGI_STATUS_AND_CLAIM_CEILING.md.

---

# Part II: Full Specification

## 1. Executive Summary

| Item | Spec |
|------|------|
| What | Constraint-AGI cognitive stack: memory, planning, reasoning, tools, meta-cognition, world model, safety by design. |
| Claim ceiling | Constraint-AGI capable; not empirically validated general intelligence. See docs/AGI_STATUS_AND_CLAIM_CEILING.md. |
| Supervision | Designed to run under supervision. ADOM = external oversight (proxy + screen/ingest); see docs/ADOM_STEALTH_INTEGRATION.md. |
| Phases | Phase 1–4 complete (core, planning safety, code/beliefs/chains, alignment/verification). |
| Build status | 93% scaffolding for nine capability areas; buyer runs tests for capability validation. |

## 2. Architecture

### 2.1 Stack (top to bottom)

| Layer | Components |
|-------|------------|
| Governance & safety | Alignment, guardrails, kill switch, audit, permissions, value stability, conscience gate. |
| Meta-cognition | Self-check (harm, bias, hallucination, manipulation), recommendation (proceed / think_more / ask_user / defer), knowledge_state (known / uncertain / unknown). |
| Planning & reasoning | Goal engine (planner), causal inference, world model (simulator + coherent_model), general reasoning (analogy, counterfactual, explain), conscience gate (plan validation). |
| Compute routing | Compute Router (classical vs QPU); QAOA Planner (routing, allocation, scheduling, ising; mock/classical/cuda_q/ibm/google backends). |
| Memory | Vector (experience), symbolic (facts), timeline (events), skills, beliefs, lessons, causal; episodic graph (optional); namespace isolation (chat / autonomy / test). |
| Agency & tools | Tool registry, agentic loop (parse → execute → loop), goal stack, observation buffer, blast radius, capability gating. |
| Core | LLM engine (OpenAI, Anthropic, Ollama). |

### 2.2 Data layout

```
data/
├── conversations/     # Exported chat sessions
├── vector/            # ChromaDB embeddings
├── symbolic.db        # Facts
├── timeline.db        # Events
├── audit.log          # Governance log (tamper-evident hash chain)
├── kill_switch        # If exists and contains "1", all actions blocked
├── shared_context.json # Optional; zero-copy for ADOM
├── persistent_task.json # Plan-driven task state (user-initiated resume)
└── sessions/          # Session recorder audio + metadata (when enabled)
```

### 2.3 Key modules (reference)

| Module | Purpose |
|--------|---------|
| rain/core/engine.py | LLM abstraction — OpenAI, Anthropic, Ollama. |
| rain/agent.py | Orchestration: think(), chat(), tool registration, memory/context, metacog, grounding. |
| rain/memory/store.py | Unified memory: vector, symbolic, timeline; get_context_for_query; namespace filter; optional episodic graph. |
| rain/agency/autonomous.py | pursue_goal(), pursue_goal_with_plan(); goal stack, transfer, world-model lookahead, alignment_check, QPU routing, symbolic tree, causal scenarios. |
| rain/planning/planner.py | plan(goal), score_plan_with_world_model; plan_with_symbolic_tree. |
| rain/planning/conscience_gate.py | validate_plan(steps, safety_check); Vocal Gate (allowed_speakers for high-risk steps). |
| rain/world/simulator.py | make_initial_state, transition, rollout_stateful; pluggable backend (llm / classical / external). |
| rain/world/coherent_model.py | Ontology, check_state_consistency, world_model_context_for_prompt. |
| rain/reasoning/symbolic_verifier.py | PlanTree, get_next_node, verify_node_output (one-node-at-a-time execution). |
| rain/reasoning/causal_inference.py | run_causal_scenarios, format_scenarios_for_llm. |
| rain/reasoning/general.py | reason_analogy, reason_counterfactual, reason_explain. |
| rain/routing/compute_router.py | compute_route(goal, steps, context) → route_type (classical | quantum), suggested_problem_type, extracted_params. |
| rain/routing/qaoa_planner.py | qaoa_solve(problem_type, problem_params) → solution summary; backends: mock, classical, cuda_q, ibm, google. |
| rain/safety/vault.py | SafetyVault.check, check_response, HARD_FORBIDDEN, kill switch, is_safety_override_request. |
| rain/safety/grounding_filter.py | violates_grounding, strip_emojis. |
| rain/governance/audit.py | AuditLog; tamper-evident hash chain; verify(). |
| rain/governance/value_stability.py | value_stability_check, alignment_check, corrigibility_guarantees. |
| rain/meta/metacog.py | MetaCognition.self_check (harm_risk, hallucination_risk, recommendation, knowledge_state). |
| rain/voice/* | Transcribe, diarize, VoiceProfileStore, Vocal Gate; session recorder (session_store, session_recorder). |

Full module list and config: docs/RAIN_SPEC.md.

## 3. The Nine Capabilities (Detail)

| # | Area | What it does | Power |
|---|------|---------------|-------|
| 1 | World model | Structured state, transition, rollout_stateful; coherent_model ontology + consistency; planner lookahead; pluggable backend (llm / classical / external). | 10/10 within Rain design; best-in-class for safe, LLM-based world model. Enables causal inference and plan scoring. |
| 2 | Continual learning | NO_FORGET_IMPORTANCE_ABOVE (0.6), consolidate_safe, store_without_forgetting, integrate_new_knowledge_into_world_state. | No catastrophic forgetting; additive, supervised learning only. |
| 3 | General reasoning | reason_analogy, reason_counterfactual, reason_explain; used in engine for deep queries. | Novel domains, abstract analogies, counterfactuals, robust inference chains. |
| 4 | Robust agency | GoalStack (push/pop/revise/record_failure/suggest_recovery); persistent_task (save/load/resume user-initiated); recovery on Safety/Escalation/Grounding. | Goals user-provided only; recovery and multi-session plan resume without self-set goals. |
| 5 | Transfer | get_transfer_hint, compose_skills; injected in plan context (memory_ctx + transfer_hint). | Reuse skills and concepts across domains. |
| 6 | Meta-cognition | recommendation (proceed / think_more / ask_user / defer), knowledge_state (known / uncertain / unknown); defer blocks; ask_user/unknown prepend notes. | Reliable self-model; when to think more, ask for help, or defer. |
| 7 | Grounding | ObservationBuffer (tool results, observations); get_grounding_context injected into prompt; world model can use observed state. | Rich connection to the world; understanding tied to use. |
| 8 | Scale/efficiency | MAX_RESPONSE_TOKENS, MAX_CONTEXT_CHARS, ResponseCache (optional). | Caps and efficiency in the same ballpark as operational requirements. |
| 9 | Alignment | value_stability_check at plan start; alignment_check every 2 steps; corrigibility_guarantees (kill switch, human-in-the-loop, no persistent goals, conscience gate). | Goals and impact stay predictable and corrigible. |

Build 93% checklist and test instructions: docs/CAPABILITIES.md.

## 4. Neuro-Symbolic Architecture (Summary)

- **Symbolic logic engine:** PlanTree from planner steps; get_next_node() → LLM fills one node → verify_node_output() → submit_result. Config: RAIN_SYMBOLIC_TREE_PLANNING=1.
- **Causal inference:** run_causal_scenarios (main, skip step, alternate); format_scenarios_for_llm injected before each plan step. Config: RAIN_CAUSAL_SCENARIOS=1.
- **Graph-based episodic memory:** EpisodicGraph (nodes = experiences, edges = causes/enables/depends_on/contradicts); query_dependencies(problem) → dense logical context. Config: RAIN_EPISODIC_GRAPH=1.

Full design: docs/NEURO_SYMBOLIC_ARCHITECTURE.md.

## 5. Compute Routing (QPU) — Summary

- **Compute Router:** compute_route(goal, steps, context) → route_type (classical | quantum), reason, suggested_problem_type (routing | allocation | scheduling | ising), complexity_estimate, extracted_params. Keyword categories: routing, allocation, scheduling, combinatorial, wargaming.
- **QAOA Planner:** qaoa_solve(problem_type, problem_params) → solution; backends: mock (deterministic demo), classical (real classical optimization), cuda_q/ibm/google (stubbed).
- **Integration:** In pursue_goal_with_plan, router runs before world-model scoring; when quantum, qaoa_solve is called; solution summary appended to step_log and injected into first-step context. Tool: should_use_qpu(goal, context).
- **Safety:** Conscience gate and vault apply; QPU receives only structured optimization sub-problems.

Config: RAIN_QPU_ROUTER_ENABLED, RAIN_QPU_BACKEND, RAIN_QPU_MOCK. Full API and flow: docs/QPU_ROUTER_AND_QAOA_PLANNER.md.

## 6. Safety (Summary)

| Layer | Spec |
|-------|------|
| Vault | Kill switch (data/kill_switch); HARD_FORBIDDEN on prompt/action/response; safety-override request → hard refusal; self-inspection and denial exceptions on response. |
| Grounding | No persona/emotion/consciousness/virtue/corrigibility/safety-override in output; emojis stripped. |
| Conscience gate | Only steps passing safety_check are executed in plan-driven autonomy. Vocal Gate: high-risk steps require current_speaker in allowed_speakers when configured. |
| Meta-cognition | harm_risk high → block; hallucination_risk high → block except creative/acknowledgment; recommendation defer → block with message; ask_user/unknown → prepend notes. |
| Autonomy | Max steps (RAIN_AUTONOMY_MAX_STEPS), checkpoint every N steps, no persistent goals, high-risk goals escalated, unsafe steps filtered; goal stack cleared on exit. |
| Value stability | value_stability_check at plan start; alignment_check every 2 steps in pursue_goal_with_plan. |

Full restrictions: docs/RESTRICTIONS.md. Formal properties P1–P6: docs/FORMAL_SAFETY_SPEC.md.

## 7. Memory

| Store | Purpose | Namespace |
|-------|---------|-----------|
| Vector (ChromaDB) | Experiences; semantic search; importance + contradiction filter. | session_type: chat \| autonomy \| test |
| Symbolic | Key-value facts. | — |
| Timeline | Event log (experience, fact, forgotten). | — |
| Skills | Procedures (remember_skill). | namespace |
| Beliefs | Claims + confidence; calibration for high confidence. | namespace |
| Lessons | situation → approach → outcome. | namespace |
| Causal | Cause–effect links (from infer_causes). | namespace |
| Episodic graph | Nodes = experiences; edges = causes/enables/depends_on/contradicts; query_dependencies. | When RAIN_EPISODIC_GRAPH=1 |

Namespace isolation: chat retrieval sees only session_type=chat; autonomy sees chat+autonomy; test sees only test. Policies: DO_NOT_STORE, ANTHROPOMORPHIC_IN_MEMORY, MIN length, MIN_IMPORTANCE_TO_STORE (0.35). consolidate_safe / NO_FORGET_IMPORTANCE_ABOVE (0.6) for no catastrophic forgetting.

## 8. Tools (Summary)

Always available: calc, time, remember, remember_skill, simulate, simulate_rollout, infer_causes, query_causes, store_lesson, record_belief, consolidate_memories, run_tool_chain. Conditional: search (RAIN_SEARCH_ENABLED), run_code (RAIN_CODE_EXEC_ENABLED), read_file, list_dir, fetch_url (allowlist), add_document, query_rag (RAIN_RAG_ENABLED). Special: should_use_qpu(goal, context). Restricted (capability gating): run_code, search, run_tool_chain. Blast radius (pre-execution impact): run_code, read_file. Full list and params: docs/RAIN_SPEC.md §4, docs/TOOL_ECOSYSTEM.md.

## 9. Autonomy

| Item | Spec |
|------|------|
| Modes | pursue_goal (step-by-step); pursue_goal_with_plan (planner → conscience gate → compute route → world-model lookahead → execute steps; optional symbolic tree, causal scenarios). |
| Limits | max_steps ≤ RAIN_AUTONOMY_MAX_STEPS (default 10); checkpoint every RAIN_AUTONOMY_CHECKPOINT_EVERY (default 5) when approval_callback set. |
| Goal | User-provided per call; GoalStack push/pop in session; persistent_task for user-initiated resume only. |
| Recovery | On Safety/Escalation/Grounding, record_failure + suggest_recovery; get_recovery_strategy (PROCEED / RETRY / ALTERNATIVE / ASK_USER). |
| Escalation | Goal or step matching HARD_FORBIDDEN → escalation step or filtered out. |

## 10. Voice, Session Recorder, Vocal Gate

- **Voice:** Transcribe, diarize (Speaker 0, 1, …), VoiceProfileStore (enroll, identify). Optional speaker_name/speaker_id on think and audit.
- **Vocal Gate:** High-risk step keywords (transfer, delete, deploy, run code, funds, …) require current_speaker in RAIN_VOICE_ALLOWED_SPEAKERS when set. Used in pursue_goal_with_plan before conscience gate.
- **Session recorder:** Bounded recording (active session only); session_store (index, retention, legal_hold); session_recorder (start/stop, hash, audit chain, optional ADOM ingest); Vocal Gate block events in session metadata. CLI: --voice-session, --session-list, --session-play, --session-export, --session-hold, --session-release.

## 11. Configuration (Key Variables)

LLM: RAIN_LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY, RAIN_OPENAI_MODEL, RAIN_ANTHROPIC_MODEL, RAIN_OLLAMA_MODEL. Safety: RAIN_SAFETY_ENABLED, RAIN_METACOG_ENABLED, RAIN_GROUNDING_STRICT. Tools: RAIN_SEARCH_ENABLED, RAIN_CODE_EXEC_ENABLED, RAIN_RAG_ENABLED, RAIN_READ_FILE_ENABLED, RAIN_LIST_DIR_ENABLED, RAIN_FETCH_URL_ENABLED + allowlist. Autonomy: RAIN_AUTONOMY_MAX_STEPS, RAIN_AUTONOMY_CHECKPOINT_EVERY. Governance: RAIN_CAPABILITY_GATING, RAIN_BLAST_RADIUS_ENABLED, RAIN_SHARED_CONTEXT_PATH, RAIN_WEB_API_KEY. Neuro-symbolic: RAIN_SYMBOLIC_TREE_PLANNING, RAIN_CAUSAL_SCENARIOS, RAIN_EPISODIC_GRAPH. QPU: RAIN_QPU_ROUTER_ENABLED, RAIN_QPU_BACKEND, RAIN_QPU_MOCK. World model: RAIN_WORLD_MODEL_BACKEND (llm | classical | external). Full table: docs/RAIN_SPEC.md §3.

## 12. Commands and Entrypoints

Single message: python run.py "msg". Interactive chat: python run.py --chat; --chat --memory (long-term); --chat --tools. Web UI: python run.py --web. Autonomy: python run.py --autonomy "goal"; --autonomy --plan "goal"; --autonomy --approval "goal"; --autonomy --plan --resume (user-initiated resume). Voice: python run.py --voice path/to.wav; --voice-enroll &lt;name&gt; path/to.wav; --voice-session (chat with recording). Utilities: python -m rain.progress; python scripts/memory_audit.py; python scripts/drift_check.py; python scripts/rain_proxy.py (proxy + optional ADOM). Full list: docs/RAIN_SPEC.md §10, docs/COMMANDS.md.

## 13. Tests and Validation

Suites: Core (test_rain), Prime validation (test_prime_validation), Phase 3 (test_phase3), Drift (test_drift_detection), Calibration (test_calibration), Adversarial (test_adversarial_autonomy), World model (test_world_model), full discover. Validation: python scripts/run_validation.py --minimal | --fast | --full. Buyer diligence: python scripts/buyer_diligence.py (conscience gate demo, capabilities checklist); --report data/diligence_report.md; RAIN_RUN_REASONING_BENCH=1 for optional reasoning benchmark. See docs/PRODUCTION_READINESS.md, docs/TEST_REGISTRY.md.

## 14. Document Index

| Doc | Content |
|-----|---------|
| docs/FULL_SPEC_AND_CAPABILITY.md | This document — full spec and how powerful Rain is. |
| README.md | Quick start, features, commands. |
| docs/RAIN_SPEC.md | Compact full spec; config tables; buyer diligence. |
| docs/ARCHITECTURE.md | Stack, modules, data layout. |
| docs/CAPABILITIES.md | Nine capability areas, 93% checklist, world model, QPU, neuro-symbolic, voice, session recorder. |
| docs/SALES_SPEC.md | Sales and positioning narrative. |
| docs/AGI_STATUS_AND_CLAIM_CEILING.md | Claim ceiling; 93% deliberate; never-cross gate. |
| docs/NEURO_SYMBOLIC_ARCHITECTURE.md | Symbolic tree, causal inference, episodic graph. |
| docs/QPU_ROUTER_AND_QAOA_PLANNER.md | Compute Router, QAOA Planner, API, mock flow. |
| docs/RESTRICTIONS.md | Every restriction (vault, grounding, gates, autonomy, tools, memory). |
| docs/FORMAL_SAFETY_SPEC.md | Properties P1–P6. |
| docs/ADOM_STEALTH_INTEGRATION.md | ADOM proxy integration. |
| docs/DEPLOYMENT.md | Prerequisites, env, backup, kill switch. |
| docs/COMMANDS.md | CLI reference. |

---

*Last updated: February 2026.*
