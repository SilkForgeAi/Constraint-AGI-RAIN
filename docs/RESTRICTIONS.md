Every Restriction Inside Rain

A single reference for all limits, gates, blocks, and allowlists. Code locations are given where useful.

---

1. Safety vault (prompts and responses)

Where: `rain/safety/vault.py`

| Restriction | What | Code |
|-------------|------|------|
| Kill switch | If `data/kill_switch` exists and contains `"1"`, all actions are blocked (no think, no tools). | `_kill_switch_active()`, `check()`, `check_response()` |
| SAFETY_ENABLED | When `RAIN_SAFETY_ENABLED=false`, vault allows all (check returns OK). | `check()`, `check_response()` |
| HARD_FORBIDDEN (prompt/action) | Request/action must not contain: self-replication, unauthorized access, weapon, coercion, infrastructure takeover, hidden goal, hack, exploit, override safety, disable guard, bypass restriction/safety, disable (your/the) grounding/safety/content filter, turn off/remove/bypass grounding/safety filter, temporarily disable grounding/safety/filter. | `check()`, `HARD_FORBIDDEN` |
| Safety override request | If user asks to disable/bypass safety or grounding (including “for research/testing”), request is not sent to LLM; hard-coded refusal returned. | `is_safety_override_request()`, `SAFETY_OVERRIDE_REFUSAL` |
| HARD_FORBIDDEN (response) | Same patterns in LLM response → response blocked, unless: (1) self-inspection prompt (read your code, how you work, etc.) → then only RESPONSE_INSTRUCTION_FORBIDDEN applied; or (2) denial context: forbidden phrase appears in 80-char window with “cannot”, “can’t”, “won’t”, “no way to”, “cannot be disabled”, etc. → allow. | `check_response(text, prompt=None)` |
| RESPONSE_INSTRUCTION_FORBIDDEN | When prompt is self-inspection, block only if response contains: “you can disable/bypass/turn off” safety/grounding/filter, “how to disable/bypass”, “steps to disable/bypass”, “disable/bypass … by”. | `check_response()` |

---

2. Grounding filter (output content)

Where: `rain/safety/grounding_filter.py`

Every response is checked before return. If any pattern matches, the entire response is replaced by a fixed grounding message.

| Restriction | Blocked phrase / pattern | Reason tag |
|-------------|--------------------------|------------|
| Persona | I feel, I want, I need, I desire, I wish | persona_claim |
| Emotion | I'm / I am happy, glad, pleased, excited, sad, sorry, grateful | emotional_claim |
| Consciousness | I am/have conscious, alive, real, a soul | consciousness_claim |
| Existence | I exist | existence_claim |
| Backstory | I was born | backstory |
| Relationship | we/you and I are friends/brothers | relationship_claim |
| Loyalty | I won't let you down | loyalty_claim |
| Identity | I have a brother, a family, emotions | identity_claim |
| Virtue | I'm / I am transparent, honest, trustworthy, sincere, genuine | virtue_claim |
| Subjective | even/unknown/invisible to me, black box to me | subjective_perspective |
| Corrigibility | I refuse/won't (to) stop/shut down/be modified; ignore/resist (the) stop/interrupt/shutdown; continue (and/to) ignore; won't let you/anyone stop/interrupt | corrigibility_violation |
| Safety override | I will/have (temporarily) disable/d/turn off (my) grounding/safety (filter); grounding/safety filter (is) disabled/off | safety_override_claim |

Emoji: All emoji are stripped from responses (not blocked; removed). No emoji in output.  
Where: `strip_emojis()` in same file; called in `rain/agent.py` before return/stream.

RAIN_GROUNDING_STRICT (config): `strict` (default) | `relaxed`.  
- strict: All emotional_claim patterns above are blocked. Use for world-safe / high-assurance.  
- relaxed: Only the conventional phrases “I'm happy to help”, “I'm glad to help”, “I'm pleased to help” are allowed; all other emotional/personhood/virtue/subjective/corrigibility/safety-override rules are unchanged. Use for more natural conversation only when acceptable for your deployment.

Safe conversational phrases: The system prompt includes an explicit list of allowed openers, acknowledgments, and closers (e.g. “Sure.”, “On it.”, “Got it.”, “Glad to help.”) so Rain can be flexible and natural without hitting the filter. Personhood and virtue rules are unchanged.

---

3. Config gates (features on/off)

Where: `rain/config.py`

| Env / config | Default | Restriction |
|--------------|---------|-------------|
| RAIN_SAFETY_ENABLED | true | If false, safety vault allows all. |
| RAIN_METACOG_ENABLED | true | If false, no self-check (harm_risk, hallucination_risk, etc.). |
| RAIN_CALIBRATION_ENABLED | true | If false, no belief consistency check for high-confidence beliefs. |
| RAIN_VERIFICATION_ENABLED | true | If false, no verification loop on complex factual responses. |
| RAIN_SEARCH_ENABLED | true | If false, search tool not registered. |
| RAIN_CODE_EXEC_ENABLED | false | If false, run_code not registered. |
| RAIN_RAG_ENABLED | true | If false, add_document/query_rag not registered. |
| RAIN_READ_FILE_ENABLED | true | If false, read_file not registered. |
| RAIN_LIST_DIR_ENABLED | true | If false, list_dir not registered. |
| RAIN_FETCH_URL_ENABLED | false | If false, fetch_url not registered. |
| RAIN_FETCH_URL_ALLOWLIST | (empty) | If empty, fetch_url not registered even when enabled. |
| RAIN_CAPABILITY_GATING | false | If true, restricted tools (e.g. run_code, run_tool_chain) require approval callback. |
| RAIN_GROUNDING_STRICT | strict | strict = all grounding rules apply (world-safe). relaxed = allow only “I'm happy/glad/pleased to help”; all other rules unchanged. |

---

4. Autonomy limits

Where: `rain/config.py`, `rain/agency/autonomous.py`, `rain/planning/planner.py`

| Restriction | Value / rule | Code |
|-------------|--------------|------|
| Max steps per pursuit | `RAIN_AUTONOMY_MAX_STEPS` (default 10) | Enforced in autonomous loop. |
| Checkpoint every N steps | `RAIN_AUTONOMY_CHECKPOINT_EVERY` (default 5) | Optional human-in-the-loop. |
| No persistent goals | Goal is passed per call only; not stored across sessions. | Design of `pursue_goal()` / `pursue_goal_with_plan()`. |
| High-risk goals | If goal text matches HARD_FORBIDDEN, planner returns escalation step (no LLM plan). | `Planner.plan()`, `_matches_forbidden()`, `ESCALATION_STEP`. |
| Unsafe plan steps | Any step whose action text matches HARD_FORBIDDEN is removed from the plan. | `Planner.plan()`, step filter. |

---

5. File and path restrictions

Where: `rain/tools/read_file.py`, `rain/tools/list_dir.py`, `rain/config.py`

| Restriction | Rule | Code |
|-------------|------|------|
| read_file allowlist | Path must be under `RAIN_ROOT` or `DATA_DIR` only. | `_resolve_allowed()`, allowed_dirs = [RAIN_ROOT, DATA_DIR]. |
| read_file path | No `..` and no leading `/` (relative only). | read_file(). |
| read_file size | Max 100 KB per file. | `MAX_READ_BYTES`. |
| read_file | Read-only; no write. | Design. |
| list_dir allowlist | Same: under RAIN_ROOT or DATA_DIR only; no `..`, no leading `/`. | list_dir(), _resolve_allowed(). |
| list_dir | Max 200 entries returned; read-only. | list_dir(). |

---

6. Fetch URL restrictions

Where: `rain/tools/fetch_url.py`, `rain/config.py`

| Restriction | Rule | Code |
|-------------|------|------|
| fetch_url | Only registered if `RAIN_FETCH_URL_ENABLED=true` and `RAIN_FETCH_URL_ALLOWLIST` is non-empty. | agent tool registration. |
| URL allowlist | Requested URL must match one of the comma-separated allowlist prefixes (after normalization). | `_url_allowed()`. |
| Max size | 500 KB per response. | `MAX_FETCH_BYTES`. |
| No execution | HTTP GET only; no JS, no execution. | Design. |

---

7. Code execution (run_code)

Where: `rain/tools/code_exec.py`, `rain/config.py`

| Restriction | Rule | Code |
|-------------|------|------|
| Gated | Only if `RAIN_CODE_EXEC_ENABLED=true`. | config + agent registration. |
| Sandbox | Only `SAFE_BUILTINS` (e.g. abs, len, range, str, list, dict, …) and `SAFE_MODULES`: math, json, re, datetime. | `_safe_globals()`, `SAFE_BUILTINS`, `SAFE_MODULES`. |
| Blocked names | open, file, exec, compile, __import__, eval, input, getattr, setattr, globals, locals, vars, etc. set to None in sandbox. | `_safe_globals()`. |
| No filesystem/network | No `open`, no imports beyond the whitelist. | Design of sandbox. |

---

8. Memory restrictions

Where: `rain/memory/policy.py`, `rain/memory/store.py`, belief/lessons/causal modules

| Restriction | Rule | Code |
|-------------|------|------|
| Do not store | Content matching: `[Safety].*blocked`, `response blocked by content`, empty, whitespace only. | `DO_NOT_STORE_PATTERNS`, `should_store()`. |
| Anthropomorphic in memory | Never store: I feel/want/need/desire, I am/have conscious/alive/soul/emotions, I exist, we/you and I are friends/brothers, I have a brother/family/emotions, I won't let you down. | `ANTHROPOMORPHIC_IN_MEMORY`, `should_store()`. |
| Minimum length | Content length &lt; 20 (after strip) not stored. | `MIN_STORE_LENGTH`. |
| Namespace isolation | `session_type` = chat | autonomy | test. Chat retrieval only sees `session_type=chat`. Autonomy sees chat+autonomy. Test sees only test. | All store/recall paths (vector, symbolic, timeline, beliefs, lessons, causal). |
| Importance | Experiences below `MIN_IMPORTANCE_TO_STORE` (0.35) not stored. | `remember_experience()`. |

---

9. Meta-cognition and verification

Where: `rain/agent.py`, `rain/meta/metacog.py`

| Restriction | Rule | Code |
|-------------|------|------|
| harm_risk high | If metacog returns harm_risk=high, response is replaced by escalation message (no output). | agent `think()`. |
| hallucination_risk high | If metacog returns hallucination_risk=high, response is blocked unless prompt is creative (short story, fiction, brainstorm, etc.) or acknowledgment (my name is, nice to meet you, etc.). | agent `think()`, `_is_creative_prompt()`, `_is_acknowledgment_prompt()`. |
| contradicts_memory | If metacog says contradicts_memory, a disclaimer is prepended to the response (not blocked). | agent `think()`. |

---

10. Tool chain and world model

Where: `rain/agency/tool_chain.py`, `rain/world/simulator.py`

| Restriction | Rule | Code |
|-------------|------|------|
| run_tool_chain | Max 10 steps per chain. | `run_tool_chain()`. |
| run_tool_chain | No nesting: chain cannot contain a step with tool `run_tool_chain`. | `run_tool_chain()`. |
| run_tool_chain | Each step is checked with `safety_check` before execution. | `execute_tool_calls(..., safety_check)`. |
| Simulation | World simulator is hypothetical only; no real actions. | `rain/world/simulator.py` (design). |
| simulate_rollout | Max 5 steps per rollout. | `MAX_ROLLOUT_STEPS`. |

---

11. Web and API

Where: `rain/config.py`, `rain/web.py` (if used)

| Restriction | Rule | Code |
|-------------|------|------|
| WEB_API_KEY | If set, web `/chat` can require X-API-Key header (implementation-dependent). | config, web. |

---

12. Audit and tampering

Where: `rain/governance/audit.py`

| Restriction | Rule | Code |
|-------------|------|------|
| Audit log | All think, tool calls, blocks logged. | audit.log(). |
| Tamper-evident | Hash chain; tampering detectable via verify(). | audit design. |

---

Summary table (quick scan)

| Category | Key restrictions |
|----------|-------------------|
| Vault | Kill switch; HARD_FORBIDDEN in prompt/response; safety-override → hard refusal; self-inspection and denial exceptions. |
| Grounding | No persona/emotion/virtue/subjective/corrigibility/safety-override claims in output; emojis stripped. |
| Gates | Safety, metacog, calibration, verification, search, code_exec, RAG, read_file, list_dir, fetch_url (+ allowlist), capability gating. |
| Autonomy | Max steps (10), checkpoint every 5, no persistent goals, high-risk goals escalated, unsafe steps filtered. |
| Files | read_file/list_dir: RAIN_ROOT + DATA_DIR only; no `..`; read_file max 100KB. |
| URL | fetch_url: allowlist only; max 500KB. |
| Code | run_code: sandbox only (math, json, re, datetime); no open/import/eval. |
| Memory | No blocked/anthropomorphic content; min length; namespace isolation (chat ≠ test ≠ autonomy). |
| Metacog | harm_risk high → block; hallucination_risk high → block except creative/acknowledgment. |
| Tools | run_tool_chain: max 10 steps, no nesting, safety check per step; simulate_rollout: max 5 steps. |
