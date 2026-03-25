"""Tool API layer — registry and execution."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

def _tool_safe(f: Callable) -> Callable:
    """Mark function as a callable tool."""
    f._rain_tool = True
    return f


class ToolRegistry:
    """Registry of tools Rain can invoke."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        params: dict | None = None,
    ) -> None:
        """Register a tool."""
        self._tools[name] = {
            "func": func,
            "description": description,
            "params": params or {},
        }

    def list_tools(self) -> list[dict]:
        """Get tool schemas for the LLM."""
        return [
            {
                "name": name,
                "description": t["description"],
                "params": t["params"],
            }
            for name, t in self._tools.items()
        ]

    def execute(self, name: str, **kwargs: Any) -> str:
        """Execute a tool by name. Returns result string."""
        if name not in self._tools:
            return f"Error: Unknown tool '{name}'"
        try:
            result = self._tools[name]["func"](**kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result)
        except Exception as e:
            return f"Error: {str(e)}"


# Built-in tools
def _calc(expression: str) -> str:
    """Evaluate a safe math expression."""
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expression):
        return "Error: Only numbers and +-*/(). allowed"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


def _time() -> str:
    """Get current date and time."""
    return datetime.now().isoformat()


def create_default_tools() -> ToolRegistry:
    """Create registry with default Phase 1 tools. remember + remember_skill added by agent."""
    reg = ToolRegistry()
    reg.register("calc", _calc, "Evaluate a math expression.", {"expression": "str"})
    reg.register("time", _time, "Get current date and time. No params.")
    return reg
