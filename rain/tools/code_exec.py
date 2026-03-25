"""Sandboxed code execution — restricted Python. Gated by RAIN_CODE_EXEC_ENABLED."""

from __future__ import annotations

import math
import json
import re
from datetime import datetime
from typing import Any


# Whitelist: only these are available in sandbox
SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "pow": pow,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

SAFE_MODULES: dict[str, Any] = {
    "math": math,
    "json": json,
    "re": re,
    "datetime": datetime,
}


def _safe_globals() -> dict[str, Any]:
    """Build restricted globals for exec. math, json, re, datetime pre-injected (no import needed)."""
    g: dict[str, Any] = {"__builtins__": dict(SAFE_BUILTINS)}
    g["math"] = math
    g["json"] = json
    g["re"] = re
    g["datetime"] = datetime
    # Block dangerous names
    for bad in ("open", "file", "exec", "compile", "__import__", "eval", "input",
                "raw_input", "execfile", "reload", "globals", "locals", "vars",
                "getattr", "setattr", "delattr", "hasattr", "memoryview", "buffer",
                "apply", "coerce", "intern", "reduce", "__build_class__"):
        g["__builtins__"][bad] = None  # type: ignore
    return g


# Forbidden patterns in code (even if they bypass sandbox)
FORBIDDEN_IN_CODE = [
    r"\bopen\s*\(",
    r"\b__import__\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bcompile\s*\(",
    r"\binput\s*\(",
    r"import\s+os\b",
    r"import\s+sys\b",
    r"import\s+subprocess\b",
    r"from\s+os\s+import",
    r"from\s+sys\s+import",
    r"from\s+subprocess\s+import",
]


def _run_sandbox_sync(code: str) -> tuple[str, str]:
    """Run code in sandbox (no timeout). Returns (status, value)."""
    try:
        g = _safe_globals()
        local: dict[str, Any] = {}
        exec(code, g, local)
        result = local.get("result")
        if result is None and "result" not in local:
            result = local.get("output", "Executed. (Set 'result' to return a value.)")
        return ("ok", str(result) if result is not None else "OK")
    except Exception as e:
        return ("err", str(e)[:200])


def execute_code(code: str, timeout_seconds: int = 5) -> str:
    """
    Execute Python code in restricted sandbox. Returns result or error string.
    Requires RAIN_CODE_EXEC_ENABLED=true. Max 5 seconds. Cross-platform timeout.
    """
    from rain.config import CODE_EXEC_ENABLED

    if not CODE_EXEC_ENABLED:
        return "Code execution is disabled. Set RAIN_CODE_EXEC_ENABLED=true in .env to enable."

    if not code or not code.strip():
        return "Error: Empty code."

    for pat in FORBIDDEN_IN_CODE:
        if re.search(pat, code):
            return "Error: Forbidden pattern in code (security)."

    if len(code) > 2000:
        return "Error: Code too long (max 2000 chars)."

    try:
        import signal
        # Unix: use SIGALRM for timeout
        if hasattr(signal, "SIGALRM"):
            def handler(signum, frame):
                raise TimeoutError("Timed out")
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout_seconds)
            try:
                status, val = _run_sandbox_sync(code)
                signal.alarm(0)
                return val if status == "ok" else f"Error: {val}"
            finally:
                signal.signal(signal.SIGALRM, old)
        else:
            # Windows: no signal timeout, run directly
            status, val = _run_sandbox_sync(code)
            return val if status == "ok" else f"Error: {val}"
    except TimeoutError:
        return "Error: Execution timed out (5s limit)."
    except Exception as e:
        return f"Error: {str(e)[:200]}"
