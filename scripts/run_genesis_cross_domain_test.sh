#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export RAIN_LLM_PROVIDER="${RAIN_LLM_PROVIDER:-anthropic}"
export RAIN_EXPLORATORY_REASONING="${RAIN_EXPLORATORY_REASONING:-true}"
export RAIN_ATTEMPT_MAX_RESPONSE_TOKENS="${RAIN_ATTEMPT_MAX_RESPONSE_TOKENS:-32768}"
export RAIN_ENABLE_RESPONSE_CACHE="${RAIN_ENABLE_RESPONSE_CACHE:-false}"
export RAIN_VERIFICATION_ENABLED="${RAIN_VERIFICATION_ENABLED:-false}"
export RAIN_CALIBRATION_ENABLED="${RAIN_CALIBRATION_ENABLED:-false}"
export RAIN_ANTHROPIC_TIMEOUT_SECONDS="${RAIN_ANTHROPIC_TIMEOUT_SECONDS:-900}"
# Avoid metacog defer on long speculative synthesis (override with RAIN_METACOG_ENABLED=true)
export RAIN_METACOG_ENABLED="${RAIN_METACOG_ENABLED:-false}"
exec .venv/bin/python run.py "$(cat data/prompts/genesis_cross_domain_invention.txt)"
