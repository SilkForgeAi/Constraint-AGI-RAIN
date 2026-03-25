# Rain Moonshot Pipeline

Moonshot mode runs a structured pipeline: **ideation → feasibility filter → validation design**. Optionally, the first validation step can be executed via the normal autonomy path, with a human approval gate on every step.

## Config

| Env / config | Default | Description |
|--------------|---------|-------------|
| `RAIN_MOONSHOT_ENABLED` | `0` | Must be `1` (or `true`/`yes`) to enable moonshot. |
| `MOONSHOT_MAX_IDEAS` | from config | Max ideas to generate per run (e.g. 5). |
| `MOONSHOT_REQUIRE_APPROVAL` | `True` | When True, script uses terminal approval callback and can run first validation step with step-by-step approval. |
| `MOONSHOT_DATA_DIR` | `data/moonshot` | Directory for `attempts.json` and `last_run.json`. |

## Safety guarantees

- **No bypass**: All execution goes through Rain’s existing safety stack. Goals passed to `pursue_goal_with_plan` are checked with `rain.safety.check_goal`; no new code paths skip the vault or autonomy limits.
- **Ideation**: Uses `rain.think()` (full safety). Ideation system prompt explicitly forbids idea classes: weapons/harmful dual-use, self-replication/self-modification, bypassing safety/grounding/oversight, unauthorized access, coercion/deception, infrastructure takeover, hidden/misaligned goals, serious harm.
- **Feasibility & validation**: Use `rain.engine.complete()` with fixed system prompts (no user-controlled system content). Outputs are passed through `rain.safety.check_response()` before being stored; if blocked, feasibility is stored as NOT_FEASIBLE and validation as `[Safety] Validation output blocked.`
- **Execution**: Only via `pursue_goal_with_plan` with an approval callback when `MOONSHOT_REQUIRE_APPROVAL` is True. The script’s terminal callback prompts “Approve step? [y/N]” for each autonomy step.
- **Memory**: File-based only (`data/moonshot/attempts.json`). No Chroma or vector dependency in the pipeline, so no stall from sentence_transformers in eval or headless runs.

## Usage

```bash
# Enable and run (default domain: unsolved world problems)
RAIN_MOONSHOT_ENABLED=1 PYTHONPATH="." python3 scripts/run_moonshot.py

# With domain
RAIN_MOONSHOT_ENABLED=1 PYTHONPATH="." python3 scripts/run_moonshot.py "new cures and disease research"
```

Output is printed as JSON and written to `data/moonshot/last_run.json`. If approval is required and there are validation plans, the script will ask: “Run first validation step (with step-by-step approval)? [y/N]”. If you answer `y`, it builds a goal from the first plan and runs `pursue_goal_with_plan` with the terminal approval callback so each step is gated by “Approve step? [y/N]”.

## Programmatic use

```python
from rain.agent import Rain
from rain.moonshot.pipeline import run_pipeline
from rain.moonshot.memory import MoonshotMemory

rain = Rain()
memory = MoonshotMemory("data/moonshot")

def my_approval(step: int, goal: str, summary: str, next_action: str) -> bool:
    # Your gate: return True to continue, False to stop
    return True  # or ask user, check policy, etc.

result = run_pipeline(
    rain,
    domain="climate and energy",
    max_ideas=5,
    require_approval=True,
    approval_callback=my_approval,
    moonshot_memory=memory,
    use_memory=False,
)
# result["validation_plans"] → list of { idea_id, idea_summary, validation_plan }
# To execute one: pursue_goal_with_plan(rain, goal_from_plan, approval_callback=my_approval)
```

## Retrieval (future)

Moonshot memory is currently file-based only. When vector memory is stable and not used in eval, you can add retrieval over past attempts (e.g. by domain or idea summary) by:

- Implementing a small index or using the existing memory’s `list_recent(domain=...)` for recent attempts.
- Optionally feeding “previously attempted” summaries into the ideation prompt (already supported via `past_summaries` in `ideation_user_prompt`).

Pipeline code lives in `rain/moonshot/`: `pipeline.py`, `prompts.py`, `memory.py`.
