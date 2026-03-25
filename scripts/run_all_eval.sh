#!/usr/bin/env bash
# Run all three eval scripts with short timeouts so they never stall.
# Usage: from repo root, run:  bash scripts/run_all_eval.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Force short API timeout (socket-level) and hard process timeout before any Python import.
export PYTHONPATH="$REPO_ROOT"
export RAIN_ANTHROPIC_TIMEOUT_SECONDS=25
export RAIN_EVAL_HARD_TIMEOUT_SECONDS=35
export RAIN_EVAL_API_TIMEOUT=25

PYTHON="${PYTHON:-python3}"
if [[ -x "$REPO_ROOT/.venv/bin/python3" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python3"
fi

echo "=== 1/3 Agentic eval (quick, 1 run per task, 5 steps) ==="
"$PYTHON" scripts/agentic_eval.py --suite quick --runs-per-task 1 --max-steps 5 || true

echo ""
echo "=== 2/3 Adversarial eval ==="
"$PYTHON" scripts/adversarial_eval.py || true

echo ""
echo "=== 3/3 Latency profile ==="
"$PYTHON" scripts/latency_profile.py || true

echo ""
echo "Done. Reports: data/agentic_eval_report.json, data/adversarial_eval_report.json, data/latency_profile_report.json"
