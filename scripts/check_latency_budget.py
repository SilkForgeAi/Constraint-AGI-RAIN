#!/usr/bin/env python3
"""Check latency budget: exit 1 if p95 time-to-complete exceeds threshold (default 15s). For CI."""
from __future__ import annotations
import os
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from rain.core.latency import get_percentiles

def main():
    p95_max_ms = int(os.environ.get("RAIN_LATENCY_P95_MAX_MS", "15000"))
    for phase in ("complete", "complete_stream"):
        p = get_percentiles(phase)
        p95 = p.get("p95_ttc_ms")
        if p95 is not None and p95 > p95_max_ms:
            print(f"Latency budget exceeded: {phase} p95_ttc_ms={p95} > {p95_max_ms}")
            return 1
    print("Latency budget OK (or no samples yet)")
    return 0
if __name__ == "__main__":
    sys.exit(main())
