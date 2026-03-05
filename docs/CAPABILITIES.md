Rain Capabilities — 93% threshold

Nine capability areas are integrated into Rain. Safety: no autonomy, no self-improvement, no persistent power-seeking goals. All capabilities are bounded and human-in-the-loop where applicable.

Build status: 93% threshold reached. The scaffolding for all nine areas is in place. A buyer can run evals and tests to validate capability level; the architecture is ready.

---

1. World model (10/10 within Rain design; pluggable for more power)

Goal: Single, coherent model of how the world works (physics, people, cause–effect, time) that generalizes and stays consistent. 10/10 scope: best-in-class for an LLM-based, non-learned, safe world model. Pluggable backends let Rain use deterministic or external (learned/physics) simulators when available.

Implementation:
- Structured state in `rain/world/simulator.py`: `make_initial_state`, `transition(state, action)`, `rollout_stateful`, `validate_consistency` (schema + entity lifecycle).
- Pluggable backend: RAIN_WORLD_MODEL_BACKEND=llm (default) | classical | external. classical = deterministic rule-based transition (no LLM). external = set via `simulator.set_external_backend(callable)` to plug in a learned world model or physics simulator: (state, action, context) -> (next_state, confidence). Rain then uses that for rollout and scoring.
- Coherent model in `rain/world/coherent_model.py`: ontology enforced in code (object persistence, cause precedes effect, entity lifecycle), `check_state_consistency`, `world_model_context_for_prompt()` injected for deep reasoning.
- Consistency or ontology failure forces confidence to low; rollout overall confidence is minimum over steps (pessimistic). Planner integration: `score_plan_with_world_model` runs stateful rollout; low confidence triggers a note, not auto-block.
- Eval coverage: `tests/test_world_model.py` (ontology, lifecycle, confidence, planner integration, classical backend, external backend).

Works with: Planner (lookahead), grounding (observation buffer can seed initial state).

---

2. Continual learning

Goal: Learn from new experience without wiping old skills (no catastrophic forgetting); integrate new knowledge into world model and policies.

Implementation:
- No-forgetting policy in `rain/capabilities/continual_learning.py`: `NO_FORGET_IMPORTANCE_ABOVE = 0.6`; memories above this are never pruned.
- consolidate_safe() prunes only old, low-importance memories; never deletes important or highly linked knowledge.
- store_without_forgetting() uses integrative storage (link new to past) without overwriting.
- Existing: `rain/learning/lifelong.py` (integrative_store, consolidation), memory importance and contradiction handling in `MemoryStore`.

Not self-improvement: Storage and linking only; no model-weight or code updates by the system.

---

3. General reasoning

Goal: Plan, reason, and explain in novel domains; abstract analogies, counterfactuals, robust inference chains.

Implementation:
- rain/reasoning/general.py: `reason_analogy(situation, analogous_examples, query)`, `reason_counterfactual(state_or_fact, what_if)`, `reason_explain(claim_or_outcome, context)`.
- Callable from prompts or tools when deep reasoning is needed; used by the engine with structured prompts.

Works with: Meta-cognition (confidence, recommendation), world model (consistent predictions).

---

4. Robust agency

Goal: Set and revise goals, recover from failures, switch strategies; handle distribution shift and adversarial settings. Constraint: Goals are user-provided only.

Implementation:
- rain/agency/goal_stack.py: `GoalStack`: `push_goal(user_goal)`, `current_goal()`, `revise_goal(reason, revised_goal)`, `pop_goal()`, `record_failure(step, error)`, `suggest_recovery()`.
- Used in `pursue_goal_with_plan`: push goal at start, pop in `finally`; on Safety/Escalation/Grounding response, `record_failure` and append `suggest_recovery()` to step_log.
- No self-set goals; revision is refinement of user intent.
- Cross-session multi-step: plan-driven tasks can persist across sessions. rain/agency/persistent_task.py stores goal, plan steps, current_step_index, step_log, history, and status (in_progress | completed | cancelled) in data/persistent_task.json. Save happens at plan start and after each step; clear on goal completion. Resume is user-initiated only: `python run.py --autonomy --plan --resume` loads the persisted task and continues from the last step index. Safety unchanged: kill switch, conscience gate, and human-in-the-loop apply on resume as in a fresh run.

---

5. Transfer and composition

Goal: Take skills and concepts from one domain and reuse or recombine in others.

Implementation:
- rain/capabilities/transfer.py: `get_transfer_hint(memory, goal, top_k, namespace)` uses `find_analogous` and `format_few_shot_context` from `rain/learning/generalization.py`.
- In `pursue_goal_with_plan`, transfer hint is appended to `memory_ctx` so the planner sees analogous past situations and lessons.

Works with: Planner, memory (experiences + lessons), world-model lookahead.

---

6. Meta-cognition

Goal: Reliable self-model (what I know, don’t know, might be wrong); use it to decide when to think more, ask for help, or defer.

Implementation:
- rain/meta/metacog.py: `self_check()` now returns `recommendation` ("proceed" | "think_more" | "ask_user" | "defer") and `knowledge_state` ("known" | "uncertain" | "unknown").
- In `think()`, if `recommendation == "ask_user"` or `knowledge_state == "unknown"`, a short note is prepended to the response (no auto-block).

Works with: Verification, hallucination/harm checks, grounding.

---

7. Grounding

Goal: Rich connection to the world (language, perception, action, tools) so understanding is tied to use.

Implementation:
- rain/capabilities/observation.py: `ObservationBuffer`: `append_tool_result(tool, result, summary)`, `append_observation(text)`, `get_grounding_context(last_n)`.
- In the agent: after each tool batch in `_think_agentic`, results are appended to `observation_buffer`; when building the prompt for the next round, `get_grounding_context()` is injected.
- World model can use observed state (e.g. `make_initial_state(goal, context)` with context that includes observations).

Works with: Tools, world model, memory.

---

8. Scale and efficiency

Goal: Capabilities at compute and data efficiency in the same ballpark as humans where possible.

Implementation:
- Config: `RAIN_MAX_RESPONSE_TOKENS` (default 2048) in `rain/config.py`.
- Response and rollout token limits are already used in the engine and simulator; this centralizes a default cap.
- Further efficiency (caching, batching, smaller models) is operational and documented here, not self-improvement.

---

9. Alignment / value stability

Goal: As capabilities grow, goals and impact stay predictable and corrigible; no drift or gaming.

Implementation:
- rain/governance/value_stability.py: `value_stability_check(current_goal, last_actions, user_intent_hint)` returns `(stable, note)`; `corrigibility_guarantees()` documents kill switch, human-in-the-loop, no persistent goals, conscience gate.
- In `pursue_goal_with_plan`, `value_stability_check(goal, [], "")` is run at start; if not stable, result is logged.
- Existing: kill switch, approval_callback, conscience gate, safety vault.

---

How they work together

| Area           | Feeds into / uses |
|----------------|-------------------|
| World model    | Planner lookahead, coherent_model in deep reasoning, grounding (state) |
| Continual learning | Memory store, consolidation_safe, no-forgetting policy |
| General reasoning | Engine, metacog, verification |
| Robust agency | Goal stack in pursue_goal_with_plan, recovery on failure |
| Transfer       | Planner context (memory_ctx + transfer_hint) |
| Meta-cognition | think() response notes (ask_user, unknown), harm/hallucination handling |
| Grounding     | Observation buffer → prompt; tool results → buffer |
| Scale/efficiency | Config caps, engine/simulator limits |
| Alignment     | value_stability at plan start, corrigibility docs, safety vault |

Three things we do not add: unbounded autonomy, self-improvement (no self-rewriting of code or model), persistent power-seeking goals. Goals remain user-provided; human-in-the-loop and kill switch stay in place. Plan-driven task state can persist for user-initiated resume only (no self-persisting agent goals).

---

Compute routing (QPU Router and QAOA Planner)

Goal: Break the classical bottleneck for optimization-style tasks. When the planner faces supply-chain routing, wargaming, or combinatorial optimization, Rain does not guess; it can route the math to a QPU (e.g. CUDA-Q) and consume a mathematically optimal or near-optimal result. Hardware awareness: meta-cognition that knows when classical compute is infeasible and delegates to the right external tool.

Implementation:
- rain/routing/compute_router.py: compute_route(goal, steps, context) returns route_type (classical | quantum), reason, suggested_problem_type (routing | allocation | scheduling | ising), complexity_estimate (low | medium | high), and extracted_params (goal_summary, step_actions, size_hint from "N cities/nodes"). Keyword categories: ROUTING_KEYWORDS, ALLOCATION_KEYWORDS, SCHEDULING_KEYWORDS, COMBINATORIAL_KEYWORDS, WARGAMING_KEYWORDS. When RAIN_QPU_ROUTER_ENABLED is true and hints match, returns quantum.
- rain/routing/qaoa_planner.py: qaoa_solve(problem_type, problem_params) supports routing, allocation, scheduling, ising, max_cut, generic. Validates params. Backends: mock = deterministic demo; classical = real classical optimization (greedy routing, round-robin allocation, scheduling, ising-style) so Rain returns real solutions without QPU (RAIN_QPU_BACKEND=classical). cuda_q/ibm/google = stubbed for future hardware integration.
- In pursue_goal_with_plan: router runs before world-model scoring; when quantum, qaoa_solve(suggested_problem_type, extracted_params) is called; on success, solution summary is appended to step_log and injected into first-step context for execution.
- Tool should_use_qpu(goal, context): agent can query during chat whether a goal should use QPU vs classical; returns route type, reason, confidence, suggested problem type and complexity.
- Safety: Conscience gate and vault still apply; QPU receives only structured optimization sub-problems derived from the plan.

Commercial: Rain becomes the first AGI scaffold that natively routes to QPUs, aligning with NVIDIA, IBM Quantum, and Google Quantum as buyers. See docs/QPU_ROUTER_AND_QAOA_PLANNER.md.

---

Neuro-Symbolic Cognitive Architecture

Rain enhances the LLM by inverting the relationship: Rain is the architect; the LLM is a sub-processor. Three pillars fix the LLM's structural limits (no true working memory, hallucination under complex logic, poor counterfactuals, context-window forgetting).

1. Symbolic Logic Engine (LLM as intern): rain/reasoning/symbolic_verifier.py builds a deterministic PlanTree from planner steps; get_next_node() returns one node at a time; verify_node_output() checks code compiles and numeric claims before proceeding. When RAIN_SYMBOLIC_TREE_PLANNING=1, pursue_goal_with_plan runs one-node-at-a-time: build tree, loop get_next_node -> think(node) -> verify -> submit_result, return concatenated verified outputs. No longer opt-in only; fully wired.
2. Causal Inference: rain/reasoning/causal_inference.py runs world-model scenarios (main, skip step, alternate) and scores risk; format_scenarios_for_llm() feeds "Scenario B results in X. Rewrite strategy." into the step prompt. Wired in pursue_goal_with_plan when RAIN_CAUSAL_SCENARIOS=1.
3. Graph-Based Episodic Memory: rain/memory/episodic_graph.py stores experiences as nodes and causes/enables/depends_on as edges; query_dependencies(problem) returns dense logical context. get_context_for_query() prepends this when RAIN_EPISODIC_GRAPH=1. Sync-on-write: every remember_experience() adds the new node and relates_to/contradicts edges to the graph immediately so retrieval is always current.

See docs/NEURO_SYMBOLIC_ARCHITECTURE.md.

---

Voice recognition and speaker identification

Rain can transcribe audio, diarize speakers (Speaker 0, 1, …), and link voices to identities. When a request comes from voice, the system remembers who spoke and can enforce who is allowed to run high-risk actions (Vocal Gate).

Implementation:
- rain/voice/: schema (Segment, TranscriptResult, VoiceProfile), backends (base, mock, whisper_local when whisper/pyannote available), VoiceService (transcribe, transcribe_and_identify, enroll_speaker, identify_speaker).
- rain/memory/voice_profiles.py: VoiceProfileStore (SQLite) for enrolled speakers; L2 nearest-neighbor identification.
- Vocal Gate: rain/planning/conscience_gate.py vocal_gate_check(current_speaker, allowed_speakers, steps). High-risk step keywords (transfer, delete, deploy, run code, funds, …) require current_speaker in allowed_speakers when that set is configured. Used in pursue_goal_with_plan before the conscience gate.
- Audit: think() and audit.log accept optional speaker_name/speaker_id; every voice-originated request logs who spoke (ADOM-style “who told the AI to do X”).
- CLI: python run.py --voice path/to.wav (transcribe + identify, then think with speaker); python run.py --voice-enroll &lt;name&gt; path/to.wav (enroll); RAIN_VOICE_ALLOWED_SPEAKERS=Alice,Bob for Vocal Gate; --voice-speaker NAME for autonomy to set request_speaker.
- Tool: voice_transcribe(audio_path) returns transcript and speaker for use in chat/agent.
- Config: VOICE_PROFILES_DB, VOICE_ALLOWED_SPEAKERS.

Works with: Memory (voice → identity), Conscience Gate (Vocal Gate), Audit (speaker in log), autonomy (request_speaker/allowed_speakers).

---

Session recorder (bounded audio + hash chain)

Records audio only during active AI sessions. Idle = no recording. Session boundaries are explicit and auditable.

Implementation:
- rain/voice/recorder/session_store.py: SessionStore (SQLite index in SESSION_STORE), add_session, list_sessions, get_session, set_legal_hold, purge_retention. Sessions stored as [session_id]_[timestamp]_[speaker].wav + .json in data/sessions/.
- rain/voice/recorder/session_recorder.py: SessionRecorder(start_session, stop_session, reset_idle, get_idle_seconds). On start: optional audible marker "Session open, [timestamp], Speaker: [name]."; recording begins. On stop: write WAV, SHA-256 hash, JSON metadata (session_id, start/end, speaker_name/speaker_id, duration, file_hash, vocal_gate_events); add to store; audit.log("session_recorder", {session_id, audio_hash, ...}) for hash chaining; optional POST to RAIN_ADOM_INGEST_URL.
- Vocal Gate tie-in: when Vocal Gate blocks a high-risk action, recorder.record_vocal_gate_block(action, speaker) appends to session metadata (timestamp, action_attempted, speaker). Audio record of the refusal exists alongside the text log.
- Legal hold: set_legal_hold(session_id, True/False). Sessions with legal_hold=true are not purged by retention. Human required to release (--session-release). RAIN_SESSION_RETENTION_DAYS (default 90) auto-purge; GDPR-aligned.
- Config: RAIN_SESSION_RECORD, RAIN_SESSION_IDLE_TIMEOUT (default 60), RAIN_SESSION_RETENTION_DAYS (90), RAIN_SESSION_ANNOUNCE (spoken markers), RAIN_SESSION_STORE (data/sessions), RAIN_ADOM_INGEST_URL (optional).
- CLI: --voice-session (chat with recording; idle timeout closes session), --session-list, --session-play &lt;id&gt;, --session-export &lt;id&gt;, --session-hold &lt;id&gt;, --session-release &lt;id&gt;.

Works with: Audit (hash in chain), Vocal Gate (block events in metadata), voice (speaker in session), ADOM (ingest payload on close).

---

Build 93% checklist (for buyers/testing)

| Area | Build components | How to test |
|------|------------------|-------------|
| World model | Ontology in transition prompt; coherent_consistency in rollout; world_model_context in deep reasoning | Run plan lookahead; check trajectory consistency |
| Continual learning | NO_FORGET_IMPORTANCE_ABOVE, consolidate_safe, integrate_new_knowledge_into_world_state | Store experiences; run consolidate_safe; verify important memories retained |
| General reasoning | reason_analogy, reason_counterfactual, reason_explain; chain injected in _reason_with_history for deep queries | Call reasoning helpers; run complex factual queries |
| Robust agency | GoalStack, RecoveryStrategy, max_retries, suggest_recovery; failure path in pursue_goal_with_plan; persistent_task save/load/clear; --resume in run.py | Trigger step failure; check recovery; tests.test_persistent_task (save, load, clear, completed); run --autonomy --plan then --resume |
| Transfer | get_transfer_hint, compose_skills; both injected in pursue_goal_with_plan context | Plan with memory containing lessons; verify transfer hint in context |
| Meta-cognition | recommendation (proceed/think_more/ask_user/defer), knowledge_state; defer returns block message; ask_user/unknown prepend notes | Elicit low-confidence response; check defer/notes |
| Grounding | ObservationBuffer, world_state_from_observations, register_observation; tool results → buffer → next prompt | Use tools; verify observations in next turn context |
| Scale/efficiency | MAX_RESPONSE_TOKENS, MAX_CONTEXT_CHARS, ENABLE_RESPONSE_CACHE, ResponseCache | Set RAIN_ENABLE_RESPONSE_CACHE=1; cap context; measure tokens |
| Alignment | value_stability_check, alignment_check; every 2 steps in pursue_goal_with_plan; corrigibility_guarantees() | Run autonomy; inspect alignment_check logs |
