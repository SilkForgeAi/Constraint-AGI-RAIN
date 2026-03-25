#!/usr/bin/env bash
# Stress test: first-principles protein nucleation / proteostasis (long answer; high token cap).
set -euo pipefail
cd "$(dirname "$0")/.."
export RAIN_MAX_RESPONSE_TOKENS="${RAIN_MAX_RESPONSE_TOKENS:-8192}"
export RAIN_ATTEMPT_MAX_RESPONSE_TOKENS="${RAIN_ATTEMPT_MAX_RESPONSE_TOKENS:-32768}"
export RAIN_ANTHROPIC_TIMEOUT_SECONDS="${RAIN_ANTHROPIC_TIMEOUT_SECONDS:-900}"
export RAIN_METACOG_ENABLED="${RAIN_METACOG_ENABLED:-false}"
exec .venv/bin/python run.py "$(cat data/prompts/stress_protein_nucleation_first_principles.txt)"
