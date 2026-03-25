#!/usr/bin/env bash
# Run Rain test suite. Skips voice/vector/RAG load to avoid segfaults on some macOS setups.
# Use: ./run_tests.sh   or   bash run_tests.sh

set -e
export RAIN_SKIP_VOICE_LOAD=1
export RAIN_DISABLE_VECTOR_MEMORY=1
export RAIN_RAG_ALWAYS_INJECT=0

if .venv/bin/python -m pytest --version &>/dev/null; then
  .venv/bin/python -m pytest -q "$@"
elif python3 -m pytest --version &>/dev/null; then
  python3 -m pytest -q "$@"
else
  echo "pytest not found. Install with: pip install pytest  or  pip install -r requirements.txt"
  echo "If .venv has no pip: python3 -m venv .venv --clear && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
