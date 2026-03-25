"""Exact math routing — substitute numeric claims with calc-verified values."""

from __future__ import annotations

import re
from typing import Callable


def _safe_expr(s: str) -> str:
    s = (s or "").strip().replace("^", "**")
    if not s or not re.match(r"^[\d\s\+\-\*\/\.\(\)\*\*]+$", s):
        return ""
    return s[:200]


def _extract_expression_from_prompt(prompt: str) -> str | None:
    if not prompt:
        return None

    m = re.search(
        r"(?:what is|calculate|compute|solve|eval(uate)?)\s*[:\s]*([\d\s\+\-\*\/\.\(\)\^]+)",
        prompt,
        re.I,
    )
    if m:
        return _safe_expr(m.group(1))

    m = re.search(r"(\d+)\s*(?:times|\*|x)\s*(\d+)", prompt, re.I)
    if m:
        return _safe_expr(f"{m.group(1)}*{m.group(2)}")

    m = re.search(r"(\d+)\s*[\+\-\*\/]\s*(\d+)", prompt)
    if m:
        return _safe_expr(m.group(0))

    return None


def _extract_final_number_from_response(response: str):
    patterns = [
        r"(?:final\s+)?answer\s*[:\s=]\s*([-+]?\d+(?:\.\d+)?)",
        r"result\s*(?:is|:|=)\s*([-+]?\d+(?:\.\d+)?)",
        r"(?:=\s*)([-+]?\d+(?:\.\d+)?)\s*$",
        r"\b([-+]?\d+(?:\.\d+)?)\s*$",
    ]
    last = None
    for pat in patterns:
        for m in re.finditer(pat, response or "", re.I):
            try:
                n = float(m.group(1))
                last = (n, m.start(1), m.end(1))
            except Exception:
                pass
    return last if last else (None, -1, -1)



def _looks_math_like_prompt(prompt: str) -> bool:
    lower = (prompt or "").lower()
    return any(
        w in lower
        for w in (
            "calculate", "compute", "solve", "equation", "equal", "equals",
            "sum", "product", "multiply", "divide", "add", "subtract", "result", "answer",
        )
    )


def _has_explicit_arithmetic_equation(text: str) -> bool:
    return bool(
        re.search(
            r"[\d\)\]]\s*[\+\-\*\/\^]\s*[\d\(\[][^\n]{0,80}=\s*[-+]?\d",
            text or "",
        )
    )


def _extract_arithmetic_equalities(response: str, max_eq: int = 5):
    if not response:
        return []
    pat = re.compile(
        r"(?P<lhs>[\d\s\+\-\*\/\.\(\)\^]{3,200})\s*=\s*(?P<rhs>[-+]?\d+(?:\.\d+)?)",
        re.I,
    )
    out = []
    for m in pat.finditer(response):
        if len(out) >= max_eq:
            break
        lhs_raw = (m.group("lhs") or "").strip()
        rhs_raw = (m.group("rhs") or "").strip()
        if not re.search(r"[\+\-\*\/\^]", lhs_raw):
            continue
        lhs = _safe_expr(lhs_raw)
        if not lhs:
            continue
        try:
            rhs_val = float(rhs_raw)
        except ValueError:
            continue
        out.append((m.start("rhs"), m.end("rhs"), lhs, rhs_val))
    return out


def _format_num(n: float) -> str:
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return str(n)


def substitute_exact_math(prompt: str, response: str, calc_fn: Callable[[str], str]) -> str:
    if not (response or "").strip():
        return response

    out = response

    # 1) Prompt-derived expression -> final answer substitution
    expr = _extract_expression_from_prompt(prompt)
    if expr:
        tool_result = calc_fn(expr)
        if tool_result and not tool_result.startswith("Error"):
            try:
                correct = float(tool_result)
            except ValueError:
                correct = None
            if correct is not None:
                num, start, end = _extract_final_number_from_response(out)
                if num is not None and start >= 0 and end >= 0 and abs(num - correct) >= 1e-9:
                    out = out[:start] + _format_num(correct) + out[end:]

    # 2) Equality corrections: <expr> = <number>
    # Guard: only apply in math-like contexts with explicit arithmetic equations.
    if _looks_math_like_prompt(prompt) and _has_explicit_arithmetic_equation(out):
        try:
            reps = []
            for rhs_start, rhs_end, lhs_expr, rhs_val in _extract_arithmetic_equalities(out, max_eq=5):
                tool_result = calc_fn(lhs_expr)
                if not tool_result or tool_result.startswith("Error"):
                    continue
                try:
                    correct = float(tool_result)
                except ValueError:
                    continue
                if abs(correct - rhs_val) < 1e-9:
                    continue
                reps.append((rhs_start, rhs_end, _format_num(correct)))

            for s, e, repl in sorted(reps, key=lambda x: x[0], reverse=True):
                out = out[:s] + repl + out[e:]
        except Exception:
            pass

    return out
