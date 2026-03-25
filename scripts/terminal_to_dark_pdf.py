#!/usr/bin/env python3
"""Render a terminal/text log to PDF: black background, white monospace text."""

from __future__ import annotations

import argparse
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _asciiish(text: str) -> str:
    try:
        from unidecode import unidecode
        return unidecode(text)
    except Exception:
        return text.encode("ascii", errors="replace").decode("ascii")


def _lines_from_text(raw: str, width_chars: int) -> list[str]:
    out: list[str] = []
    for line in raw.splitlines():
        line = line.replace("\t", "    ")
        if len(line) <= width_chars:
            out.append(line)
        else:
            out.extend(
                textwrap.wrap(
                    line, width=width_chars, break_long_words=True, break_on_hyphens=False
                )
            )
    return out


def terminal_to_pdf(
    input_path: Path,
    output_path: Path,
    *,
    font_size: float = 7.5,
    width_chars: int = 96,
    top_margin: float = 0.45 * inch,
    bottom_margin: float = 0.45 * inch,
    side_margin: float = 0.45 * inch,
) -> None:
    raw = input_path.read_text(encoding="utf-8", errors="replace")
    raw = _asciiish(raw)
    lines = _lines_from_text(raw, width_chars)

    page_w, page_h = letter
    c = canvas.Canvas(str(output_path), pagesize=letter)

    line_height = font_size * 1.25
    usable_h = page_h - top_margin - bottom_margin
    lines_per_page = max(1, int(usable_h / line_height))

    def paint_page_bg() -> None:
        c.setFillColor(black)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        c.setFillColor(white)

    paint_page_bg()
    y = page_h - top_margin
    c.setFont("Courier", font_size)

    for i, line in enumerate(lines):
        if i > 0 and i % lines_per_page == 0:
            c.showPage()
            paint_page_bg()
            c.setFont("Courier", font_size)
            y = page_h - top_margin
        s = line if len(line) <= width_chars + 20 else line[: width_chars + 17] + "..."
        c.drawString(side_margin, y - font_size, s)
        y -= line_height

    c.save()


def main() -> None:
    p = argparse.ArgumentParser(description="Terminal log -> dark PDF (white on black)")
    p.add_argument("input", type=Path, help="Path to terminal .txt log")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: data/terminal_<stem>_<utc>.pdf)",
    )
    args = p.parse_args()
    inp = args.input.expanduser().resolve()
    if not inp.is_file():
        raise SystemExit("Not a file: %s" % (inp,))

    if args.output:
        out = args.output.expanduser().resolve()
    else:
        data = Path(__file__).resolve().parent.parent / "data"
        data.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%SZ")
        out = data / ("terminal_%s_%s.pdf" % (inp.stem, ts))

    out.parent.mkdir(parents=True, exist_ok=True)
    terminal_to_pdf(inp, out)
    print(out)


if __name__ == "__main__":
    main()
