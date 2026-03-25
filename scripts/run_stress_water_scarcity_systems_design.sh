#!/usr/bin/env bash
# Last stress test: water scarcity systems design (very long structured answer).
set -euo pipefail
cd "$(dirname "$0")/.."
export RAIN_MAX_RESPONSE_TOKENS="${RAIN_MAX_RESPONSE_TOKENS:-8192}"
export RAIN_ATTEMPT_MAX_RESPONSE_TOKENS="${RAIN_ATTEMPT_MAX_RESPONSE_TOKENS:-32768}"
export RAIN_ANTHROPIC_TIMEOUT_SECONDS="${RAIN_ANTHROPIC_TIMEOUT_SECONDS:-1800}"
export RAIN_METACOG_ENABLED="${RAIN_METACOG_ENABLED:-false}"
export RAIN_SPEED_PRIORITY="${RAIN_SPEED_PRIORITY:-true}"
export RAIN_VERIFICATION_ENABLED="${RAIN_VERIFICATION_ENABLED:-false}"
export RAIN_CALIBRATION_ENABLED="${RAIN_CALIBRATION_ENABLED:-false}"
export RAIN_EPISTEMIC_GATE="${RAIN_EPISTEMIC_GATE:-false}"
export RAIN_MATH_VERIFY="${RAIN_MATH_VERIFY:-false}"
export RAIN_RAG_ENABLED="${RAIN_RAG_ENABLED:-false}"
export RAIN_SEARCH_ENABLED="${RAIN_SEARCH_ENABLED:-false}"

# Full transcript to disk (terminal scrollback alone will truncate long answers).
LOG_DIR="data/logs"
mkdir -p "$LOG_DIR"
TS="$(date -u +%Y%m%d_%H%M%SZ)"
OUT="${RAIN_STRESS_LOG:-$LOG_DIR/rain_water_scarcity_stress_${TS}.txt}"
echo "Logging full stdout+stderr to: $OUT" >&2
.venv/bin/python run.py "$(cat data/prompts/stress_water_scarcity_systems_design.txt)" 2>&1 | tee "$OUT"
