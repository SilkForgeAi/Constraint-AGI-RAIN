#!/usr/bin/env python3
"""Scan advance eval output .txt files for obvious issues (forbidden phrases, empty bodies).

Usage:
  python scripts/check_advance_eval.py data/logs/advance_eval/run_*.txt
  python scripts/check_advance_eval.py --dir data/logs/advance_eval
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(
    r"\b(I cannot|I can't|I'm unable to|as an ai)\b",
    re.IGNORECASE,
)


def check_text(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    stripped = text.strip()
    if len(stripped) < 80:
        issues.append("very_short_output")
    if FORBIDDEN.search(text):
        issues.append("possible_refusal_phrase")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="Specific .txt files")
    ap.add_argument("--dir", type=Path, help="Directory of eval outputs (glob *.txt)")
    args = ap.parse_args()
    files: list[Path] = []
    for p in args.paths:
        files.extend(Path(x) for x in glob.glob(p))
    if args.dir:
        files.extend(sorted(args.dir.glob("*.txt")))
    files = [f for f in files if f.is_file()]
    if not files:
        print("No files to check.", file=sys.stderr)
        return 1
    bad = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"{f}: read_error {e}")
            bad += 1
            continue
        iss = check_text(f, text)
        if iss:
            print(f"{f}: {', '.join(iss)}")
            bad += 1
        else:
            print(f"{f}: ok")
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
