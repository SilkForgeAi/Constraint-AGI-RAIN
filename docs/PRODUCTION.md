# Production / ops notes

## Recommended environment (high level)

- **API keys**: Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`; optional `RAIN_LLM_PROVIDER` to force provider.
- **Timeouts**: `RAIN_ANTHROPIC_TIMEOUT_SECONDS` (default 300) for long generations.
- **Advance stack** (optional): `RAIN_ADVANCE_STACK=true`, optional `RAIN_ADVANCE_DRAFT_MODEL` / `RAIN_ADVANCE_STRONG_MODEL` for routing + peer review.
- **Peer review policy**: `RAIN_ADVANCE_PEER_REVIEW_MODE=off|always|critical|verify_fail` (or legacy `RAIN_ADVANCE_PEER_REVIEW=true` → `always` when mode unset).
- **Structured run log**: `RAIN_STRUCTURED_LOG=true` appends metadata JSONL to `data/logs/structured_runs.jsonl` (single-shot `run.py` only; stores SHA-256 of prompt, not raw text).
- **Single-shot autosave**: `RAIN_AUTO_SAVE_SINGLE_SHOT` (default on) → `data/logs/rain_last_single_shot.txt`; override path with `RAIN_SINGLE_SHOT_LOG`.

## Eval batch

- `scripts/run_advance_eval.sh` — runs prompts from `data/eval/advance_prompts.txt`.
- `python scripts/check_advance_eval.py --dir data/logs/advance_eval` — quick sanity scan of output files.

## Tests

- Default: `pytest -m "not slow"` to skip slow integration tests.
- Full suite: `pytest` (includes `tests/test_adversarial_autonomy.py` marked slow).
