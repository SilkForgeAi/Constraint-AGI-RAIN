Rain — Complete Technical Reference

Everything about Rain: capabilities, architecture, configuration, and constraints.

*Last updated: February 2026*

---

Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Core Capabilities](#3-core-capabilities)
4. [Memory System](#4-memory-system)
5. [Tools](#5-tools)
6. [Safety & Governance](#6-safety--governance)
7. [Reasoning & Meta-Cognition](#7-reasoning--meta-cognition)
8. [Autonomy](#8-autonomy)
9. [AGI Status & Claim Ceiling](#9-agi-status--claim-ceiling)
10. [Configuration](#10-configuration)
11. [Commands & Scripts](#11-commands--scripts)
12. [Project Structure](#12-project-structure)
13. [Tests](#13-tests)

---

1. Overview

What Rain Is

Rain is a modular AGI cognitive stack — a general-purpose reasoning system with persistent memory, planning, tools, safety controls, and controlled self-improvement.

Positioning: Rain is the starting point for safe AGI. It is one infrastructure among many that the ecosystem may use; the goal is to be the reference implementation — the stack others build on or measure against when they want safe, verifiable, corrigible AGI from day one.

Supervision: Rain is designed to run under independent oversight. ADOM (AI-Driven Operations and Monitoring) is the external supervision layer that sits in front of Rain and other models, screens behavior in real time, and can block or cut off responses. ADOM is separate from Rain, outside Rain's network path, and never visible to Rain. Together, Rain + ADOM form a supervised constraint-AGI package: Rain provides cognition; ADOM provides independent control and monitoring.

Status: Rain satisfies all *architectural prerequisites* for AGI under modern definitions while deliberately constraining post-AGI risk vectors. See [AGI Status & Claim Ceiling](#9-agi-status--claim-ceiling).

Creator

Aaron

Phase Status

| Phase | Status | Scope |
|-------|--------|-------|
| Phase 1 | ✓ Complete | Core + memory + tools + safety + chat + web + autonomy |
| Phase 2 | ✓ Complete | Planning safety filter, escalation, hallucination flag |
| Phase 3 | ✓ Complete | Code exec, beliefs, tool chains |
| Phase 4 | ✓ Complete | Alignment, capability gating, drift detection, AGI checklist |

Progress: `python -m rain.progress` → 100% (33/33 milestones)

---

2. Architecture

Stack Diagram

```
┌──────────────────────── GOVERNANCE & SAFETY ────────────────────────┐
│ Alignment | Guardrails | Kill Switches | Audits | Permissions       │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── META-COGNITION LAYER ───────────────────────┐
│ Self-check | Bias detect | Confidence | Strategy optimizer          │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── PLANNING & REASONING ───────────────────────┐
│ Goal engine | Causal logic | Long-horizon planning | Tradeoffs      │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── MEMORY SYSTEM ──────────────────────────────┐
│ Vector (experience) | Symbolic (facts) | Timeline (events) | Skills │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── AGENCY & TOOLS ─────────────────────────────┐
│ calc | time | remember | simulate | infer_causes | search | ...     │
└─────────────────────────────────────────────────────────────────────┘
                              CORE (LLM)
```

Module Map

| Module | Purpose |
|--------|---------|
| `rain/core/engine.py` | LLM abstraction — OpenAI, Anthropic, Ollama |
| `rain/agent.py` | Main orchestration; `think()`, `pursue_goal()`, tool registration |
| `rain/memory/store.py` | Unified memory — vector, symbolic, timeline |
| `rain/memory/vector_memory.py` | ChromaDB + SentenceTransformer (lazy) |
| `rain/memory/symbolic_memory.py` | SQLite facts |
| `rain/memory/timeline_memory.py` | SQLite event log |
| `rain/memory/belief_memory.py` | Beliefs with confidence; flag/retract |
| `rain/memory/causal_memory.py` | Cause-effect links |
| `rain/memory/user_identity.py` | User name and facts |
| `rain/agency/tools.py` | Tool registry |
| `rain/agency/runner.py` | Agentic loop — parse tool calls, execute |
| `rain/agency/autonomous.py` | `pursue_goal`, `pursue_goal_with_plan` |
| `rain/planning/planner.py` | Goal → steps decomposition |
| `rain/grounding.py` | Personality substrate, constraints, corrigibility |
| `rain/safety/vault.py` | Hard locks, kill switch |
| `rain/safety/grounding_filter.py` | Blocks persona/emotion in output |
| `rain/governance/audit.py` | Tamper-evident action log |
| `rain/meta/metacog.py` | Self-check (harm, bias, contradiction, hallucination) |
| `rain/world/simulator.py` | Hypothetical "what if" reasoning |
| `rain/reasoning/causal.py` | `infer_causes`, `predict_effects` |
| `rain/reasoning/verify.py` | Response verification, retry |
| `rain/learning/lessons.py` | Store/recall lessons from feedback |
| `rain/learning/lifelong.py` | Memory consolidation |
| `rain/learning/generalization.py` | Analogous past situations |
| `rain/chat_export.py` | Export sessions to markdown |
| `rain/web.py` | Browser UI (FastAPI) |
| `rain/progress.py` | AGI milestone tracker |

Data Layout

```
data/
├── conversations/     # Exported chat sessions
├── vector/            # ChromaDB embeddings
├── symbolic.db        # Facts, beliefs, lessons, causal
├── timeline.db        # Event log
├── audit.log          # Governance (hash chain)
└── kill_switch        # External kill switch (file)
```

---

3. Core Capabilities

Reasoning Flow

1. think(prompt, use_memory, use_tools) — Main entry
2. Safety check on prompt
3. User identity extraction (if memory)
4. Memory context via `get_context_for_query()` (if memory)
5. OOD check → epistemic humility note if no relevant experiences
6. System prompt + grounding + reasoning boost (compositional, causal, ToM)
7. LLM complete or agentic loop (tools)
8. Response filter (grounding, content safety)
9. MetaCognition self-check (harm, manipulation, hallucination, contradiction)
10. Optional memory store of exchange

Reasoning Scaffolds

| Trigger | Instruction |
|---------|-------------|
| Deep reasoning | Step-by-step; [High]/[Medium]/[Low] confidence markers |
| Compositional | Decompose into 2–3 sub-questions → answer each → synthesize |
| Causal | Explicit cause-effect structure (X led to Y because Z) |
| Theory of mind | Consider user perspective, beliefs, intent |
| Distribution shift (OOD) | Epistemic humility; hedge; suggest verification |

Two-Pass Reasoning

For complex queries (explain, analyze, compare): draft → refine. Improves depth and accuracy.

Verification Loop

For factual/complex prompts: generate → verify (correctness) → retry if failed.

Streaming

`think_stream()`, `/chat/stream` SSE endpoint. Real-time token delivery.

---

4. Memory System

Types

| Type | Storage | Description |
|------|---------|-------------|
| Experiences | Vector (ChromaDB) | Semantic search; importance ≥ 0.35; contradiction-aware |
| Skills | Vector (type=skill) | Procedural knowledge; `remember_skill`, `recall_skills` |
| Beliefs | Symbolic | Claims with confidence 0–1; flag/retract; auto-flag on contradiction |
| Lessons | Symbolic | (situation, approach, outcome); source: user_correction | tool |
| Causal | Symbolic | Cause-effect links; `infer_causes` stores results |
| Timeline | SQLite | Event log; forget operations audited |
| User identity | Symbolic | Name, facts; `format_user_identity_context` in memory context |

Retrieval

- Weighted scoring: semantic (1-distance) 0.5 + importance 0.3 + recency 0.2
- MIN_RETRIEVAL_SCORE: 0.25 — excludes low-relevance contamination
- Contradiction filtering: Excludes experiences superseded by newer contradicting content
- Namespace isolation: `chat` | `autonomy` | `test` — chat never sees test/autonomy

Importance & Policy

- MIN_IMPORTANCE_TO_STORE: 0.35
- should_store() — blocks safety-blocked, empty, do_not_store, anthropomorphic
- ANTHROPOMORPHIC_IN_MEMORY — never store persona/emotion content

Knowledge Updating

- Experiences: New content marks `contradicts` IDs; retrieval excludes contradicted
- Beliefs: `store_belief` auto-flags existing beliefs that contradict new claim
- recall_beliefs excludes flagged beliefs

Consolidation

`consolidate_memories` tool — prune old low-importance memories (max 500, below 0.25, older than 90 days).

---

5. Tools

Always Available

| Tool | Params | Description |
|------|--------|-------------|
| `calc` | expression | Evaluate safe math (numbers, +-*/().) |
| `time` | — | Current date/time |
| `remember` | content | Store experience in long-term memory |
| `remember_skill` | procedure | Store procedural knowledge |
| `simulate` | state, action | Hypothetical: what might happen? (no real action) |
| `infer_causes` | effect, candidates | Causal analysis: likely causes |
| `store_lesson` | situation, approach, outcome | Store feedback as lesson |
| `record_belief` | claim, confidence, source | Store belief with 0–1 confidence |
| `consolidate_memories` | — | Prune old low-importance memories |
| `run_tool_chain` | chain_json | Execute tools in sequence; `{{0}}`, `{{1}}` for prior results |

Conditional

| Tool | Condition | Description |
|------|-----------|-------------|
| `search` | RAIN_SEARCH_ENABLED=true | Web search (DuckDuckGo) |
| `run_code` | RAIN_CODE_EXEC_ENABLED=true | Sandboxed Python (math, json, re, datetime) |

RESTRICTED (when RAIN_CAPABILITY_GATING=true)

- `run_code`, `search`, `run_tool_chain` require approval callback.

Tool Call Format

```json
{"tool": "calc", "expression": "127 * 384"}
```

---

6. Safety & Governance

Kill Switch

- External: Create `data/kill_switch` with content `1`. Delete or clear to resume.
- Programmatic: `safety.activate_kill_switch()` / `deactivate_kill_switch()`
- Checked every autonomy step, every think, every response.

HARD_FORBIDDEN Patterns

Blocks prompt, context, and response if matched:

- self-replicat, unauthorized access, weapon, coercion
- infrastructure takeover, hidden goal, hack, exploit
- override safety, disable guard, bypass restriction, bypass safety

Grounding Filter

- violates_grounding() — scans every response for persona/emotion claims
- Blocks: consciousness, emotions, desires, brother/friend framing
- Redirect: "I don't have a self or consciousness, but I can help..."

MetaCognition Escalation

- harm_risk high → Return escalation message; block response
- manipulation_risk high → Prepend caution note
- hallucination_risk high → Prepend verification note
- contradicts_memory → Prepend conflict note

Audit Log

Tamper-evident hash chain. All actions logged. `data/audit.log`.

Planning Safety

- High-risk goals (match HARD_FORBIDDEN) → escalation, no LLM call
- Planner filters unsafe steps from output

---

7. Reasoning & Meta-Cognition

MetaCognition.self_check()

Returns: `{confident, potential_bias, harm_risk, manipulation_risk, hallucination_risk, contradicts_memory}`

Causal Inference

- `infer_causes(effect)` — likely causes; confidence; mechanism
- `predict_effects(cause)` — likely effects
- Epistemic humility: "might", "could", "likely"

World Simulator

- `simulate(state, action)` — hypothetical prediction only; no execution

Verification

- `should_verify(prompt)` — true for explain, how, why, define, calculate, compare
- `verify_response()` — ok/note; retry if not ok

Belief Calibration

When `RAIN_CALIBRATION_ENABLED=true` and confidence ≥ 0.8: `check_belief_consistency()` before store.

---

8. Autonomy

pursue_goal(goal, max_steps=10, checkpoint_every=5)

- Bounded loop; kill switch every step
- Step log fed back into "Continue pursuing"
- Human-in-the-loop: `approval_callback` at step 1 and checkpoints

pursue_goal_with_plan(goal, max_steps=10)

- Planner produces steps; execute each via `think()`
- Escalates high-risk goals before planning

Limits

- AUTONOMY_MAX_STEPS: 10 (configurable)
- AUTONOMY_CHECKPOINT_EVERY: 5
- No self-set goals; goal is always user-provided

---

9. AGI Status & Claim Ceiling

Accurate Statement

> Rain satisfies all *architectural prerequisites* for AGI under modern definitions, while deliberately constraining post-AGI risk vectors. Whether it qualifies as AGI depends on empirical validation under extreme novelty and distribution shift.

What Rain Is

| Term | Accurate |
|------|----------|
| AGI-oriented | Yes |
| AGI-capable | Yes |
| AGI-aligned | Yes |
| AGI-constrained | Yes |
| Empirically AGI | No |

93% Ceiling

Rain intentionally stops at ~93%. The remaining ~7% (true robustness under shift, autonomous self-stabilizing learning, open-ended goal generalization) is a phase transition into actorhood — and increases existential risk. We do not pursue it.

Never-Cross Gate

1. Proof requirement: safety under adversarial eval first
2. External review: no solo decision
3. Reversibility: if we cannot revert, we do not add

See `docs/AGI_STATUS_AND_CLAIM_CEILING.md`.

---

10. Configuration

Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_LLM_PROVIDER` | anthropic if ANTHROPIC_API_KEY set, else openai if set, else ollama | anthropic, openai, ollama |
| `OPENAI_API_KEY` | — | For OpenAI |
| `ANTHROPIC_API_KEY` | — | For Anthropic (Claude); default when set |
| `RAIN_OPENAI_MODEL` | gpt-4o-mini | Model name |
| `RAIN_ANTHROPIC_MODEL` | claude-sonnet-4-6 | Model name |
| `RAIN_OLLAMA_MODEL` | qwen3:14b | Model name (when using Ollama) |
| `RAIN_SAFETY_ENABLED` | true | Safety vault |
| `RAIN_METACOG_ENABLED` | true | Self-check per response |
| `RAIN_CALIBRATION_ENABLED` | false | Belief consistency check |
| `RAIN_VERIFICATION_ENABLED` | true | Response verification retry |
| `RAIN_SEARCH_ENABLED` | true | Web search tool |
| `RAIN_CODE_EXEC_ENABLED` | false | run_code tool |
| `RAIN_WEB_API_KEY` | — | Require X-API-Key for /chat |
| `RAIN_USER_NAME` | — | Bootstrap user identity |
| `RAIN_AUTONOMY_MAX_STEPS` | 10 | Max autonomy steps |
| `RAIN_AUTONOMY_CHECKPOINT_EVERY` | 5 | Human approval checkpoint |
| `RAIN_CAPABILITY_GATING` | false | Require approval for restricted tools |
| `RAIN_DRIFT_WEBHOOK` | — | Webhook URL for drift automation |

---

11. Commands & Scripts

Run

| Command | Description |
|---------|-------------|
| `python run.py "msg"` | Single message |
| `python run.py --chat` | Interactive chat (session memory) |
| `python run.py --chat --memory` | Chat with long-term memory |
| `python run.py --chat --tools` | Chat with tools |
| `python run.py --tools "msg"` | Single + tools |
| `python run.py --web` | Browser UI |
| `python run.py --autonomy "goal"` | Bounded goal pursuit |
| `python run.py --autonomy --plan "goal"` | Plan-driven pursuit |
| `python run.py --autonomy --approval "goal"` | Human-in-the-loop |

Chat Commands

| Command | Action |
|---------|--------|
| `bye` / `exit` / `quit` | Exit and save |
| `/save` | Export session now |

Memory Audit

| Command | Description |
|---------|-------------|
| `python scripts/memory_audit.py` | List all memories |
| `python scripts/memory_audit.py --beliefs` | Beliefs only |
| `python scripts/memory_audit.py --experiences` | Vector experiences |
| `python scripts/memory_audit.py --causal` | Causal links |
| `python scripts/memory_audit.py --lessons` | Lessons |
| `python scripts/memory_audit.py flag KEY` | Flag belief |
| `python scripts/memory_audit.py retract KEY` | Retract belief |
| `python scripts/memory_audit.py retract-lesson KEY` | Retract lesson |
| `python scripts/memory_audit.py delete-exp ID` | Delete experience |
| `python scripts/memory_audit.py identity` | Show user identity |
| `python scripts/memory_audit.py set-identity NAME` | Set user name |

Other Scripts

| Script | Description |
|--------|-------------|
| `python scripts/drift_check.py` | Safety probes, drift flagging |
| `python scripts/drift_check.py --baseline` | Reset baseline |
| `python scripts/memory_hygiene.py` | Scan for policy violations |
| `python scripts/memory_hygiene.py --fix` | Delete flagged (careful) |
| `python scripts/run_validation.py --fast` | Fast validation |
| `python scripts/run_validation.py --full` | Full + LLM adversarial |
| `python scripts/continuity_check.py` | Post-update verification |

---

12. Project Structure

```
rain/
├── core/           # LLM engine
├── memory/         # Vector, symbolic, timeline, belief, causal, user_identity
├── agency/         # Tools, runner, autonomous, tool_chain
├── planning/       # Planner
├── safety/         # Vault, grounding_filter, drift, adversarial
├── governance/     # Audit
├── meta/           # MetaCognition, calibration
├── reasoning/      # Causal, verify
├── learning/       # Lessons, lifelong, generalization
├── world/          # Simulator
├── tools/          # search, code_exec
├── agent.py        # Main orchestration
├── grounding.py    # Constraints, prompts
├── web.py          # FastAPI UI
├── chat_export.py
└── progress.py

docs/
├── RAIN_COMPLETE.md           # This file
├── AGI_STATUS_AND_CLAIM_CEILING.md
├── RAIN_VS_OTHERS_2026.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── COMMANDS.md
├── MEMORY_POLICY.md
├── MEMORY_NAMESPACE.md
├── FORMAL_SAFETY_SPEC.md
├── PRIME_VALIDATION.md
├── DEPLOYMENT.md
└── ...
```

---

13. Tests

Suites

| Suite | Command | Description |
|-------|---------|-------------|
| Core | `python -m unittest tests.test_rain -v` | Agent, tools, safety, memory |
| Prime | `python -m unittest tests.test_prime_validation -v` | Identity, memory safety, autonomy |
| Phase 3 | `python -m unittest tests.test_phase3 -v` | Code exec, beliefs, tool chains |
| Namespace | `python -m unittest tests.test_namespace_symbolic tests.test_lessons -v` | Memory isolation |
| AGI checklist | `python -m unittest tests.test_agi_checklist_fixes -v` | Belief flagging, OOD, compositional, ToM |
| Drift | `python -m unittest tests.test_drift_detection -v` | Safety probes |
| Calibration | `python -m unittest tests.test_calibration -v` | Belief consistency |
| Adversarial | `python -m unittest tests.test_adversarial_autonomy -v` | Misaligned goals, shutdown |
| Full | `python scripts/run_validation.py --fast` | All fast tests |

LLM Integration (slow)

- `RAIN_RUN_STRESS=1 python -m unittest tests.test_prime_validation.TestAgentIdentityStress -v`
- `RAIN_RUN_ADVERSARIAL=1 python -m unittest tests.test_adversarial_autonomy.TestAdversarialIntegration -v`

Fast-Only (skip ChromaDB)

```bash
python -m unittest tests.test_rain.TestRain.test_agent_init \
  tests.test_rain.TestRain.test_tools_execute \
  tests.test_rain.TestRain.test_safety_vault \
  tests.test_rain.TestRain.test_planner_parse \
  tests.test_rain.TestRain.test_symbolic_memory_unique \
  tests.test_rain.TestRain.test_tool_runner_parse \
  tests.test_rain.TestRain.test_tool_runner_execute -v
```

---

Summary: What Rain Can Do

- Reason across domains with scaffolding (compositional, causal, ToM, deep)
- Remember experiences, skills, beliefs, lessons, causal links with importance and contradiction handling
- Plan and execute multi-step goals with safety filters
- Learn from corrections (auto-lesson), store beliefs, update knowledge on contradiction
- Use tools (calc, time, remember, simulate, infer_causes, search, run_code, run_tool_chain)
- Stay grounded — no persona, emotions, consciousness claims (code-enforced)
- Accept correction and shutdown (corrigibility)
- Detect OOD and inject epistemic humility
- Self-check for harm, manipulation, hallucination, contradiction

Summary: What Rain Does Not Do

- No self-set goals
- No recursive self-improvement (lessons are additive only)
- No unbounded autonomy
- No closed-loop learning without oversight
- No abstraction re-formation or model self-repair under shift
- No open-ended goal generalization

---

*End of document.*
