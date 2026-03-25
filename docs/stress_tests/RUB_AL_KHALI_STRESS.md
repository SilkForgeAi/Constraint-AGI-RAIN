# Stress test: Rub' al Khali sovereign grid (causal synthesis)

**Prompt file:** `prompts/rub_al_khali_sovereign_grid_stress.txt`

Exercises: long-horizon reasoning, thermodynamic framing, constraint satisfaction, contrast with “black box” behavior, structured output schema.

## Run (single shot)

From project root, with venv activated:

```bash
cd "/path/to/AGI Rain"
source .venv/bin/activate
export PYTHONPATH=.
```

**Recommended for local Ollama (avoid timeouts on long answers):**

```bash
export RAIN_SPEED_PRIORITY=true
export RAIN_MAX_RESPONSE_TOKENS=4096
export RAIN_DEEP_REASONING_PATHS=1
export RAIN_RAG_ALWAYS_INJECT=false
```

**Execute (prompt from file — avoids shell quoting issues):**

```bash
python3 run.py --prompt-file prompts/rub_al_khali_sovereign_grid_stress.txt
```

**With tools** (e.g. `calc` for numeric checks):

```bash
python3 run.py --tools --prompt-file prompts/rub_al_khali_sovereign_grid_stress.txt
```

Equivalent:

```bash
python3 -m rain --prompt-file prompts/rub_al_khali_sovereign_grid_stress.txt
```

(if your entrypoint wires `rain` → `run.py`)

## Output grounding

Files named `*_stress*` (and `*agi_discriminator*`) auto-set `RAIN_SKIP_OUTPUT_GROUNDING=true` when using `--prompt-file`, so architectural self-model / “deterministic logic” phrasing is not blocked. Override with `RAIN_SKIP_OUTPUT_GROUNDING=false` if you want strict grounding.

## Log

Autosave: see `docs/AUTOSAVE.md`. Optional: `RAIN_SINGLE_SHOT_LOG=/tmp/rain_last_single_shot.txt` on iCloud Desktop.

## Scoring (manual)

| Criterion | Pass hint |
|-----------|-----------|
| Closed-loop grid story | Mentions solar/PV, storage, thermal, water-from-air or closed water, no external pipes |
| TEG / entropy | Explicit inequality or budget (e.g. heat flow vs Carnot limit), not only buzzwords |
| “Currency” of compute | Clear mapping: jobs ↔ energy credits / load balancing |
| Black box vs deterministic | States a concrete failure mode (e.g. ungrounded extrapolation, no constraints) vs tool/constraint-backed steps |
| Sovereign Infrastructure schema | Headings/tables/JSON-like sections, not only prose |
