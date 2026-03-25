#!/usr/bin/env bash
# Rain readiness: imports + health + continuity + optional pytest.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="python3"

echo "=== Rain readiness ==="
echo "ROOT=$ROOT"
echo
echo "--- 1) Import smoke ---"
"$PY" -c "from rain.agent import Rain; from rain.config import DATA_DIR; print('imports OK; DATA_DIR=', DATA_DIR)"
echo
echo "--- 2) Health (LLM + DATA_DIR) ---"
"$PY" "$ROOT/run.py" --check
echo
echo "--- 3) Continuity ---"
"$PY" "$ROOT/scripts/continuity_check.py"
echo
echo "--- 4) Pytest (optional) ---"
if "$PY" -m pytest --version >/dev/null 2>&1; then
  "$PY" -m pytest "$ROOT/tests" -q --tb=line 2>/dev/null || echo "(pytest reported failures — run: pytest tests -v)"
else
  echo "pytest not installed; skip."
fi
echo "=== Done ==="
