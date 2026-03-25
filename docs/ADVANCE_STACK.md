# Rain Advance Stack

The **Advance Stack** is an **opt-in** layer that **adds** capabilities without changing Rain’s default behavior when disabled.

## Principles

1. **Default off** — `RAIN_ADVANCE_STACK` defaults to `false`. Existing installs behave as before.
2. **Additive** — Extra system instructions and optional peer review **append**; they do not remove safety, grounding, or verification tiers.
3. **Auditable** — Routing and peer-review events append to `data/logs/advance_events.jsonl` (JSONL, one object per line).
4. **Composable** — Works with memory, RAG, verification, metacog, and existing “tier” features.

## Enable

```bash
export RAIN_ADVANCE_STACK=true
```

Optional:

| Variable | Meaning |
|----------|--------|
| `RAIN_ADVANCE_DRAFT_MODEL` | Fast/cheap model id for **short, simple** prompts (heuristic). |
| `RAIN_ADVANCE_STRONG_MODEL` | Strong model id for complex prompts **and** for optional peer review. |
| `RAIN_ADVANCE_PEER_REVIEW=true` | After the main answer, one extra call appends a **## Peer review** section (requires `RAIN_ADVANCE_STRONG_MODEL`). |
| `RAIN_ADVANCE_UNCERTAINTY_PROMPT=true` | Inject epistemic discipline (tags, falsification, unknowns). Default on when stack is on. |

**Model routing** only activates when **both** `RAIN_ADVANCE_DRAFT_MODEL` and `RAIN_ADVANCE_STRONG_MODEL` are set. Otherwise the engine keeps your normal `RAIN_ANTHROPIC_MODEL` / `RAIN_OPENAI_MODEL`.

## What this is not

- Not a guarantee of “superintelligence.”
- Not a substitute for domain validation, physical tests, or policy review.
- Peer review adds **latency and cost**; use sparingly.

## Regression / smoke eval

```bash
bash scripts/run_advance_eval.sh
```

Reads `data/eval/advance_prompts.txt` (override with `RAIN_EVAL_PROMPTS=...`), writes per-prompt logs under `data/logs/advance_eval/`. Set `RAIN_ADVANCE_STACK=true` (default in script) to exercise the stack end-to-end.
