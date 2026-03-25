#!/bin/bash
# Run Rain web UI — use this if python run.py --web doesn't work
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
echo "Rain web UI: http://127.0.0.1:8765"
uvicorn rain.web:app --host 0.0.0.0 --port 8765 --reload
