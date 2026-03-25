#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rain.agent import Rain

CASES = [
    ("math_exact_quick", "Calculate 192 * 0.85 and return only the numeric answer."),
    ("logic_quick", "If all A are B and all B are C, can any A be not C? One short sentence."),
]

def main() -> None:
    rain = Rain()
    results = []
    for cid, prompt in CASES:
        out = rain.think(prompt, use_tools=True, use_memory=False, memory_namespace="test")
        results.append({"id": cid, "prompt": prompt, "response": out, "len": len(out or "")})

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cases": len(CASES),
        "results": results,
    }

    out_dir = Path("docs/stress_tests/logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eval_harness_quick.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote: {out_path}")

if __name__ == "__main__":
    main()
