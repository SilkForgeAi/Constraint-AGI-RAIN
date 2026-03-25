#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] && set -a && source .env && set +a
export RAIN_GI_STACK="${RAIN_GI_STACK:-true}"
export RAIN_GI_STRICT="${RAIN_GI_STRICT:-true}"
export RAIN_ROUTER_V2="${RAIN_ROUTER_V2:-true}"
export RAIN_STRUCTURED_MEMORY_V2="${RAIN_STRUCTURED_MEMORY_V2:-true}"
export RAIN_SESSION_TASK_WORLD="${RAIN_SESSION_TASK_WORLD:-true}"
export RAIN_VERIFY_STRICT="${RAIN_VERIFY_STRICT:-true}"
PROMPT_FILE="${1:-$ROOT/prompts/agi_discriminator.txt}"
[[ -f "$PROMPT_FILE" ]] || { echo "Missing: $PROMPT_FILE" >&2; exit 1; }
[[ -n "${RAIN_RUNNER_CMD:-}" ]] || { echo "Set RAIN_RUNNER_CMD or add to .env" >&2; exit 1; }
if [[ "${RAIN_PROMPT_MODE:-stdin}" == "arg" ]]; then
  exec bash -c "$RAIN_RUNNER_CMD \"\$1\"" bash "$PROMPT_FILE"
else
  exec bash -c "$RAIN_RUNNER_CMD" < "$PROMPT_FILE"
fi
