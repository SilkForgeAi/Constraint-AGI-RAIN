#!/usr/bin/env python3
"""Run creativity metrics (novelty, usefulness, surprise) on a list of ideas. Optional: pass domain and use LLM judge."""
from __future__ import annotations
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from rain.creativity.eval import novelty_ngram, score_creativity

def main():
    # Demo: novelty only (no engine) on a few sample ideas
    refs = [
        "Climate change can be addressed by renewable energy and policy.",
        "Product ideas should focus on user experience and scalability.",
    ]
    ideas = [
        "Use bacterial enzymes in oceans to capture CO2 and sink it as carbonate.",
        "A marketplace that matches unused lab equipment to researchers by location and need.",
    ]
    print("Creativity eval (novelty_ngram only, no LLM)")
    for i, idea in enumerate(ideas):
        nov = 1.0 - novelty_ngram(idea, refs, n=3)
        print(f"  Idea {i+1}: novelty_ngram={nov:.3f}")
    # With engine and domain we could call score_creativity(idea, refs, engine=..., domain="climate", include_llm=True)
    print("Done. For full metrics (usefulness, surprise) pass an engine and domain in code.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
