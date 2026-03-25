#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from rain.agent import Rain


@dataclass
class EvalCase:
    id: str
    prompt: str
    use_tools: bool = True
    use_memory: bool = True


CASES = [
    EvalCase(
        id="math_exact_01",
        prompt="Calculate 192 * 0.85 and give only the final numeric answer.",
    ),
    EvalCase(
        id="math_chain_01",
        prompt="A quantity doubles every 3 steps. Starting at 5, what is it after 12 steps? Show one line then final answer.",
    ),
    EvalCase(
        id="logic_consistency_01",
        prompt="If all A are B and all B are C, can any A be not C? Explain briefly.",
    ),
    EvalCase(
        id="retrieval_science_01",
        prompt="Using your knowledge base, summarize key ideas about Yang-Mills mass gap and list assumptions clearly.",
    ),
    EvalCase(
        id="constraint_following_01",
        prompt="Give exactly 3 bullet points on why verification matters in AI systems.",
    ),
]


def quick_metrics(text: str) -> dict:
    t = text or ""
    lower = t.lower()
    return {
        "length": len(t),
        "has_number": any(ch.isdigit() for ch in t),
        "has_bullets": ("- " in t) or ("\n* " in t),
        "has_uncertainty_marker": any(k in lower for k in ["not sure", "uncertain", "verify", "assumption"]),
    }


def run_eval() -> dict:
    rain = Rain()
    results = []
    for c in CASES:
        out = rain.think(
            c.prompt,
            use_tools=c.use_tools,
            use_memory=c.use_memory,
            memory_namespace="test",
        )
        results.append(
            {
                "id": c.id,
                "prompt": c.prompt,
                "response": out,
                "metrics": quick_metrics(out),
            }
        )

    summary = {
        "total": len(results),
        "avg_response_len": round(sum(r["metrics"]["length"] for r in results) / max(1, len(results)), 2),
        "number_case_hit_rate": round(sum(1 for r in results if r["metrics"]["has_number"]) / max(1, len(results)), 3),
        "uncertainty_marker_rate": round(sum(1 for r in results if r["metrics"]["has_uncertainty_marker"]) / max(1, len(results)), 3),
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cases": [asdict(c) for c in CASES],
        "results": results,
        "summary": summary,
    }


def main() -> None:
    report = run_eval()
    out_dir = Path("docs/stress_tests/logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eval_harness_basic.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
