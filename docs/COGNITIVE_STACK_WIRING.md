# Cognitive stack wiring (how pieces connect)

## Single choke point (pre-LLM)

`Rain._cognitive_pre_llm_system()` calls `rain.integration.cognitive_inject.apply_pre_llm_system()` on the **assembled system prompt** before every LLM call on these paths:

| Path | `use_tools` | Notes |
|------|----------------|-------|
| `_reason_with_history` | `false` | Default `think()` / `run.py` single-shot |
| `_reason_with_history_stream` | `false` | Streaming |
| `_think_agentic_inner` | `true` | `--tools` / agentic loop |

That function (when modules and env flags allow) applies:

- **Session task / world** — `SESSION_TASK_WORLD_ENABLED` (`RAIN_SESSION_TASK_WORLD`)
- **GI stack** — `GI_STACK_ENABLED` (`RAIN_GI_STACK`; strict routing: `RAIN_GI_STRICT`)
- **Router v2** — `ROUTER_V2_ENABLED` (`RAIN_ROUTER_V2`), additive system text from GI mode

If imports fail, the helper **falls back to the original system string** (no crash).

## Other layers (already in `think()`)

- **Advance stack** — `routing_context` + `extra_system_instructions` from `rain/advance/stack.py` (`RAIN_ADVANCE_STACK`)
- **Memory / RAG / self-model / continuous world** — injected into **user-side context** (`memory_ctx`) before `_reason_with_history`
- **Output grounding** — `violates_grounding` after generation; eval bypass via `_is_agi_discriminator_eval_prompt` / `RAIN_SKIP_OUTPUT_GROUNDING` / `_skip_output_grounding()`
- **Peer review / verification** — `maybe_peer_review_append`, `verify_response`, etc.

## Env flags (see `rain/config.py`)

```text
RAIN_GI_STACK=true
RAIN_GI_STRICT=true
RAIN_ROUTER_V2=true
RAIN_SESSION_TASK_WORLD=true
RAIN_ADVANCE_STACK=false   # optional draft/strong routing + extras
```

`STRUCTURED_MEMORY_V2_ENABLED` is defined in config; if you add facades, hook them in `think()` where `memory_ctx` is built, or extend `cognitive_inject.py`—keep one story for “where memory shape enters the prompt.”
