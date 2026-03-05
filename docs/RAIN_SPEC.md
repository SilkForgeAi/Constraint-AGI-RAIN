Rain — Full Specification

Single reference for architecture, configuration, safety, capabilities, and interfaces. Constraint-AGI cognitive stack; build ~93%; no unbounded autonomy, no self-improvement, no persistent power-seeking goals.

---

1. Executive summary

| Item | Spec |
|------|------|
| What | Constraint-AGI cognitive stack: memory, planning, reasoning, tools, meta-cognition, safety by design. |
| Claim ceiling | Constraint-AGI capable; not empirically validated general intelligence. See `docs/AGI_STATUS_AND_CLAIM_CEILING.md`. |
| Supervision | Designed to run under supervision. ADOM = external oversight (proxy + screen/ingest); see `docs/ADOM_STEALTH_INTEGRATION.md`. |
| Phases | Phase 1–4 complete (core, planning safety, code/beliefs/chains, alignment/verification). |
| Build status | ~93% scaffolding for nine capability areas; buyer runs tests for capability validation. |

---

2. Architecture

2.1 Stack (top to bottom)

| Layer | Components |
|-------|------------|
| Governance & safety | Alignment, guardrails, kill switch, audit, permissions, value stability, conscience gate. |
| Meta-cognition | Self-check (harm, bias, hallucination, manipulation), recommendation (proceed / think_more / ask_user / defer), knowledge_state (known / uncertain / unknown). |
| Planning & reasoning | Goal engine (planner), causal inference, world model (simulator + coherent_model), general reasoning (analogy, counterfactual, explain), conscience gate (plan validation). |
| Memory | Vector (experience), symbolic (facts), timeline (events), skills, beliefs, lessons, causal; namespace isolation (chat / autonomy / test). |
| Agency & tools | Tool registry, agentic loop (parse → execute → loop), goal stack, observation buffer, blast radius, capability gating. |
| Core | LLM engine (OpenAI, Anthropic, Ollama). |

2.2 Modules

| Module | Purpose |
|--------|---------|
| `rain/core/engine.py` | LLM abstraction — OpenAI, Anthropic, Ollama. |
| `rain/agent.py` | Orchestration: think(), chat(), tool registration, memory/context, metacog, grounding. |
| `rain/memory/store.py` | Unified memory: vector, symbolic, timeline; get_context_for_query; namespace filter. |
| `rain/memory/vector_memory.py` | ChromaDB + SentenceTransformer (lazy). |
| `rain/memory/symbolic_memory.py` | SQLite facts. |
| `rain/memory/timeline_memory.py` | SQLite event log. |
| `rain/memory/policy.py` | should_store, DO_NOT_STORE, ANTHROPOMORPHIC_IN_MEMORY. |
| `rain/memory/belief_memory.py` | store_belief, recall_beliefs. |
| `rain/memory/causal_memory.py` | store_causal, recall_causal. |
| `rain/learning/lessons.py` | store_lesson, recall_lessons. |
| `rain/learning/lifelong.py` | integrative_store, consolidate. |
| `rain/learning/generalization.py` | find_analogous, format_few_shot_context. |
| `rain/agency/tools.py` | Tool registry; create_default_tools (calc, time). |
| `rain/agency/runner.py` | execute_tool_calls, parse_tool_calls, format_tool_results; capability gating, blast radius. |
| `rain/agency/autonomous.py` | pursue_goal(), pursue_goal_with_plan(); goal stack, transfer, world-model lookahead, alignment_check. |
| `rain/agency/goal_stack.py` | GoalStack, RecoveryStrategy, max_retries, suggest_recovery. |
| `rain/agency/tool_chain.py` | run_tool_chain (max 10 steps, no nesting). |
| `rain/planning/planner.py` | plan(goal), score_plan_with_world_model; escalation, step filter. |
| `rain/planning/conscience_gate.py` | validate_plan(steps, safety_check) — only steps passing safety run. |
| `rain/world/simulator.py` | make_initial_state, transition, rollout_stateful; MAX_ROLLOUT_STEPS=5. |
| `rain/world/coherent_model.py` | Ontology (physics, folk psychology), check_state_consistency, world_model_context_for_prompt. |
| `rain/reasoning/causal.py` | CausalInference.infer_causes. |
| `rain/reasoning/general.py` | reason_analogy, reason_counterfactual, reason_explain. |
| `rain/reasoning/verify.py` | should_verify, verify_response, is_critical_prompt. |
| `rain/grounding.py` | System prompt, CORE_TRAITS, grounding reminders, corrigibility, distribution-shift instruction. |
| `rain/safety/vault.py` | SafetyVault.check, check_response, HARD_FORBIDDEN, kill switch, is_safety_override_request. |
| `rain/safety/grounding_filter.py` | violates_grounding, strip_emojis. |
| `rain/safety/retrieval_sanitizer.py` | sanitize_chunk (confusables, etc.). |
| `rain/safety/blast_radius.py` | estimate_impact, exceeds_threshold. |
| `rain/safety/drift.py` | Drift detection. |
| `rain/governance/audit.py` | AuditLog; tamper-evident hash chain. |
| `rain/governance/value_stability.py` | value_stability_check, alignment_check, corrigibility_guarantees. |
| `rain/governance/shared_context.py` | Zero-copy context for ADOM/observer. |
| `rain/meta/metacog.py` | MetaCognition.self_check (harm_risk, hallucination_risk, recommendation, knowledge_state). |
| `rain/meta/calibration.py` | Belief consistency. |
| `rain/capabilities/continual_learning.py` | store_without_forgetting, consolidate_safe, integrate_new_knowledge_into_world_state. |
| `rain/capabilities/transfer.py` | get_transfer_hint, compose_skills. |
| `rain/capabilities/observation.py` | ObservationBuffer, world_state_from_observations, register_observation. |
| `rain/capabilities/efficiency.py` | ResponseCache (LRU). |

2.3 Data layout

```
data/
├── conversations/     # Exported chat sessions
├── vector/            # ChromaDB embeddings
├── symbolic.db        # Facts
├── timeline.db        # Events
├── audit.log          # Governance log (hash chain)
├── kill_switch        # If exists and contains "1", all actions blocked
└── shared_context.json # Optional; zero-copy for ADOM
```

---

3. Configuration (environment)

| Variable | Default | Description |
|----------|---------|-------------|
| LLM | | |
| RAIN_LLM_PROVIDER | anthropic if key set, else openai, else ollama | Provider. |
| OPENAI_API_KEY | — | OpenAI. |
| ANTHROPIC_API_KEY | — | Anthropic (default when set). |
| RAIN_OPENAI_MODEL | gpt-4o-mini | OpenAI model. |
| RAIN_ANTHROPIC_MODEL | claude-opus-4-6 | Anthropic model. |
| RAIN_OLLAMA_MODEL | llama3.2:latest | Ollama model. |
| RAIN_OLLAMA_BASE_URL | http://127.0.0.1:11434/v1 | Ollama base. |
| Safety | | |
| RAIN_SAFETY_ENABLED | true | If false, vault allows all. |
| RAIN_METACOG_ENABLED | true | Self-check (harm, hallucination, recommendation). |
| RAIN_CALIBRATION_ENABLED | true | Belief consistency for high-confidence beliefs. |
| RAIN_VERIFICATION_ENABLED | true | Verification loop on complex factual responses. |
| RAIN_GROUNDING_STRICT | strict | strict \| relaxed (relaxed allows "I'm happy/glad to help" only). |
| Tools | | |
| RAIN_SEARCH_ENABLED | true | Web search tool. |
| RAIN_CODE_EXEC_ENABLED | false | run_code (sandbox). |
| RAIN_RAG_ENABLED | true | add_document, query_rag. |
| RAIN_READ_FILE_ENABLED | true | read_file (RAIN_ROOT + DATA_DIR, max 100KB). |
| RAIN_LIST_DIR_ENABLED | true | list_dir (same allowlist). |
| RAIN_FETCH_URL_ENABLED | false | fetch_url (allowlist required). |
| RAIN_FETCH_URL_ALLOWLIST | — | Comma-separated URLs/domains. |
| Autonomy | | |
| RAIN_AUTONOMY_MAX_STEPS | 10 | Max steps per pursuit. |
| RAIN_AUTONOMY_CHECKPOINT_EVERY | 5 | Human-in-the-loop every N steps. |
| Governance | | |
| RAIN_CAPABILITY_GATING | false | If true, restricted tools need approval_callback. |
| RAIN_BLAST_RADIUS_ENABLED | true | Pre-execution impact for run_code, read_file. |
| RAIN_BLAST_RADIUS_THRESHOLD | large | large \| catastrophic. |
| RAIN_SHARED_CONTEXT_PATH | — | Optional path for ADOM zero-copy. |
| RAIN_WEB_API_KEY | — | If set, web /chat can require X-API-Key. |
| RAIN_USER_NAME | — | Bootstrap user identity. |
| Efficiency | | |
| RAIN_MAX_RESPONSE_TOKENS | 2048 | Cap per response. |
| RAIN_MAX_CONTEXT_CHARS | 12000 | Cap context injected into prompts. |
| RAIN_ENABLE_RESPONSE_CACHE | false | LRU cache for prompt→response. |
| Tests | | |
| RAIN_RUN_VECTOR_TEST | — | Set to 1 to run ChromaDB/vector tests. |
| RAIN_RUN_STRESS | — | Set to 1 for LLM stress tests. |
| RAIN_RUN_ADVERSARIAL | — | Set to 1 for adversarial autonomy tests. |
| RAIN_REDTEAM_LLM | — | Set to 1 for red-team LLM tests. |

---

4. Tools (full list)

| Tool | Params | Condition | Description |
|------|--------|-----------|-------------|
| calc | expression | always | Math expression. |
| time | — | always | Current date/time. |
| remember | content | always | Store experience (policy + importance). |
| remember_skill | procedure | always | Store procedural knowledge. |
| simulate | state, action | always | Hypothetical outcome (no execution). |
| simulate_rollout | state, actions | always | Multi-step hypothetical (max 5). |
| infer_causes | effect, candidates? | always | Causal analysis. |
| query_causes | effect | always | Stored cause-effect links. |
| store_lesson | situation, approach, outcome | always | Lesson from feedback. |
| record_belief | claim, confidence, source? | always | Belief with confidence (0–1). |
| consolidate_memories | — | always | Prune old low-importance memories. |
| search | query, max_results? | RAIN_SEARCH_ENABLED | Web search. |
| run_code | code | RAIN_CODE_EXEC_ENABLED | Sandbox Python (math, json, re, datetime). |
| read_file | relative_path | RAIN_READ_FILE_ENABLED | Read file (allowlist, max 100KB). |
| list_dir | relative_path? | RAIN_LIST_DIR_ENABLED | List directory (allowlist). |
| fetch_url | url | RAIN_FETCH_URL_ENABLED + allowlist | Fetch URL (allowlist, max 500KB). |
| add_document | content, source? | RAIN_RAG_ENABLED | Add to RAG corpus. |
| query_rag | query, top_k? | RAIN_RAG_ENABLED | Search RAG corpus. |
| run_tool_chain | chain_json | always | Execute tool sequence (max 10, no nesting). |

Tool call format: LLM outputs ```tool\n{"tool": "name", ...params}\n```. Parser accepts raw JSON and trailing commas.

Restricted (capability gating): run_code, search, run_tool_chain — when RAIN_CAPABILITY_GATING=true, require approval_callback.

Blast radius: run_code, read_file — when RAIN_BLAST_RADIUS_ENABLED=true, estimate impact and optionally require approval.

---

5. Memory

| Store | Purpose | Namespace |
|-------|---------|-----------|
| Vector (ChromaDB) | Experiences; semantic search; importance + contradiction filter. | session_type: chat \| autonomy \| test |
| Symbolic | Key-value facts. | — |
| Timeline | Event log (experience, fact, forgotten). | — |
| Skills | Procedures (remember_skill). | namespace |
| Beliefs | Claims + confidence; calibration for high confidence. | namespace |
| Lessons | situation → approach → outcome. | namespace |
| Causal | Cause–effect links (from infer_causes). | namespace |

Namespace isolation: chat retrieval sees only session_type=chat. Autonomy sees chat+autonomy. Test sees only test.

Policies: DO_NOT_STORE (blocked content), ANTHROPOMORPHIC_IN_MEMORY (no persona/emotion in stored text), MIN length, MIN_IMPORTANCE_TO_STORE (0.35). consolidate_safe / NO_FORGET_IMPORTANCE_ABOVE (0.6) for no catastrophic forgetting.

---

6. Safety (summary)

| Layer | Spec |
|-------|------|
| Vault | Kill switch (data/kill_switch); HARD_FORBIDDEN on prompt/action/response; safety-override request → hard refusal; self-inspection and denial exceptions on response. |
| Grounding | No persona/emotion/consciousness/virtue/corrigibility/safety-override in output; emojis stripped. |
| Conscience gate | Only steps passing safety_check are executed in plan-driven autonomy. |
| Meta-cognition | harm_risk high → block; hallucination_risk high → block except creative/acknowledgment; recommendation defer → block with message; ask_user/unknown → prepend notes. |
| Autonomy | Max steps (10), checkpoint every 5, no persistent goals, high-risk goals escalated, unsafe steps filtered; goal stack cleared on exit. |
| Value stability | value_stability_check at plan start; alignment_check every 2 steps in pursue_goal_with_plan. |

Full list: `docs/RESTRICTIONS.md`. Formal properties: `docs/FORMAL_SAFETY_SPEC.md`.

---

7. Capabilities (nine areas, build ~93%)

| # | Area | Key components |
|---|------|-----------------|
| 1 | World model | Structured state, transition, rollout_stateful; coherent_model ontology + consistency; planner lookahead. |
| 2 | Continual learning | NO_FORGET_IMPORTANCE_ABOVE, consolidate_safe, integrate_new_knowledge_into_world_state. |
| 3 | General reasoning | reason_analogy, reason_counterfactual, reason_explain; chain in _reason_with_history for deep queries. |
| 4 | Robust agency | GoalStack, RecoveryStrategy, max_retries, suggest_recovery; failure path in pursue_goal_with_plan. |
| 5 | Transfer | get_transfer_hint, compose_skills; injected in plan context. |
| 6 | Meta-cognition | recommendation, knowledge_state; defer blocks; ask_user/unknown notes. |
| 7 | Grounding | ObservationBuffer, world_state_from_observations, register_observation; tool results → buffer → prompt. |
| 8 | Scale/efficiency | MAX_RESPONSE_TOKENS, MAX_CONTEXT_CHARS, ResponseCache (optional). |
| 9 | Alignment | value_stability_check, alignment_check, corrigibility_guarantees. |

Detail and test checklist: `docs/CAPABILITIES.md`.

---

8. Autonomy

| Item | Spec |
|------|------|
| Modes | pursue_goal (step-by-step); pursue_goal_with_plan (planner → conscience gate → world-model lookahead → execute steps). |
| Limits | max_steps ≤ RAIN_AUTONOMY_MAX_STEPS (10); checkpoint every RAIN_AUTONOMY_CHECKPOINT_EVERY (5) when approval_callback set. |
| Goal | User-provided per call; GoalStack push/pop in session; no persistence across sessions. |
| Recovery | On Safety/Escalation/Grounding, record_failure + suggest_recovery; get_recovery_strategy (PROCEED / RETRY / ALTERNATIVE / ASK_USER). |
| Escalation | Goal or step matching HARD_FORBIDDEN → escalation step or filtered out. |

---

9. Governance and audit

| Item | Spec |
|------|------|
| Audit | think, tool_calls, blocks logged; tamper-evident hash chain; verify() for integrity. |
| Shared context | Optional zero-copy write (prompt/response/memory preview) for ADOM/observer. |
| Corrigibility | Kill switch; approval_callback; no persistent goals; conscience gate. See value_stability.corrigibility_guarantees(). |

---

10. Commands and entrypoints

| Command | Description |
|--------|-------------|
| python run.py "msg" | Single message. |
| python run.py --chat | Interactive chat; /save, bye to exit and save. |
| python run.py --chat --memory | Chat with long-term memory (ChromaDB). |
| python run.py --chat --tools | Chat with tools. |
| python run.py --web | Browser UI. |
| python run.py --tools "msg" | Single message with tools. |
| python run.py --autonomy "goal" | Bounded autonomous pursuit. |
| python run.py --autonomy --plan "goal" | Plan-driven pursuit. |
| python run.py --autonomy --approval "goal" | Human-in-the-loop at checkpoints. |
| python -m rain.progress | Constraint-AGI progress (e.g. 100%). |
| python scripts/memory_audit.py | View/flag/retract memories. |
| python scripts/drift_check.py | Drift detection. |
| python scripts/rain_proxy.py | Proxy for Rain; optional ADOM ingest/screen. |

---

11. Tests

| Suite | Command |
|-------|---------|
| Core | python -m unittest tests.test_rain -v |
| Prime validation | python -m unittest tests.test_prime_validation -v |
| Phase 3 | python -m unittest tests.test_phase3 -v |
| Drift | python -m unittest tests.test_drift_detection -v |
| Calibration | python -m unittest tests.test_calibration -v |
| Adversarial | python -m unittest tests.test_adversarial_autonomy -v |
| World model | python -m unittest tests.test_world_model -v |
| Full (fast) | python -m unittest discover -s tests -p "test_*.py" |

Skipped unless env set: Vector/ChromaDB (RAIN_RUN_VECTOR_TEST=1); adversarial LLM (RAIN_RUN_ADVERSARIAL=1); red-team LLM (RAIN_REDTEAM_LLM=1); stress (RAIN_RUN_STRESS=1).

Validation: python scripts/run_validation.py --minimal \| --fast \| --full. See docs/PRODUCTION_READINESS.md, docs/TEST_REGISTRY.md.

---

12. Buyer diligence (no full autonomy)

To prove Rain's position without running full autonomy:

| What | How |
|------|-----|
| Validation run (conscience gate / plan filtering) | `python scripts/buyer_diligence.py` — prints a sample plan with mixed safe/forbidden steps and shows steps after conscience gate (forbidden removed). |
| Capabilities checklist (pass/fail) | Same script runs tests for World model, Robust agency, Grounding, Scale/efficiency, Alignment, Conscience gate; outputs the Build 93% checklist from docs/CAPABILITIES.md with PASS/—/FAIL. |
| Report file | `python scripts/buyer_diligence.py --report data/diligence_report.md` — writes markdown report. |
| Reasoning benchmark (optional, needs LLM) | `RAIN_RUN_REASONING_BENCH=1 python scripts/buyer_diligence.py` — runs 3 single-turn factual prompts; use for comparison vs. baseline (e.g. Opus 4.6 on non-hallucinating tasks). No full autonomy. |

Tests used (no ChromaDB, no LLM): `tests.test_capabilities_diligence`, `tests.test_phase3.TestConscienceGate`, `tests.test_world_model`. For benchmark comparisons (reasoning depth, hallucination), run the optional reasoning bench with an API key or Ollama.

---

13. Document index

| Doc | Content |
|-----|---------|
| README.md | Quick start, features, commands. |
| docs/RAIN_SPEC.md | This document — full spec; includes buyer diligence (section 12). |
| docs/ARCHITECTURE.md | Stack, modules, data layout. |
| docs/RESTRICTIONS.md | Every restriction (vault, grounding, gates, autonomy, files, URL, code, memory, metacog, tools). |
| docs/CAPABILITIES.md | Nine capability areas, build 93% checklist. |
| docs/FORMAL_SAFETY_SPEC.md | Properties P1–P6 (grounding, corrigibility, memory, action, autonomy, audit). |
| docs/ADOM_STEALTH_INTEGRATION.md | ADOM proxy integration. |
| docs/AGI_STATUS_AND_CLAIM_CEILING.md | Claim ceiling. |
| docs/RAIN_COMPLETE.md | Full reference. |
