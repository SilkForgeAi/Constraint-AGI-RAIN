#!/usr/bin/env python3
"""Print latency percentiles (p50, p95) for LLM calls. Run after or during use for CI or weekly report."""
from __future__ import annotations
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from rain.core.latency import get_percentiles
for phase in ("complete", "complete_stream"):
    p = get_percentiles(phase)
    if p.get("p50_ttc_ms") is not None or p.get("p50_ttft_ms") is not None:
        print(phase, p)
print("# Set RAIN_SPEED_PRIORITY=1 for faster thinking (streaming, fewer optional calls)")
