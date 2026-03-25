"""Agentic tool loop — parse tool calls from LLM, execute, loop."""

from __future__ import annotations

import json
import re
from typing import Any

# High-impact tools that require explicit approval when CAPABILITY_GATING_ENABLED.
RESTRICTED_TOOLS: frozenset[str] = frozenset({"run_code", "search", "run_tool_chain", "run_quantum_experiment"})

# Tools that get blast-radius (pre-execution impact) check when BLAST_RADIUS_ENABLED.
BLAST_RADIUS_TOOLS: frozenset[str] = frozenset({"run_code", "read_file"})


def format_tools_for_prompt(tools: list[dict]) -> str:
    """Format tool list for LLM consumption."""
    lines = ["Available tools. To use one, output a JSON block:\n```tool\n{\"tool\": \"NAME\", ...params}\n```"]
    for t in tools:
        name = t["name"]
        desc = t["description"]
        params = t.get("params") or {}
        param_str = ", ".join(f"{k}: {v}" for k, v in params.items()) if params else "no params"
        lines.append(f"- {name}: {desc} ({param_str})")
    return "\n".join(lines)


def _try_parse_json(s: str) -> dict | None:
    """Parse JSON, tolerate trailing commas."""
    s = re.sub(r",\s*}", "}", s)  # trailing comma before }
    s = re.sub(r",\s*]", "]", s)  # trailing comma before ]
    try:
        return json.loads(s.strip())
    except json.JSONDecodeError:
        return None


def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extract tool invocations from LLM response. Returns list of {tool, **params}."""
    out = []
    # 1. Match ```tool ... ``` or ```json ... ```
    for m in re.finditer(r"```(?:tool|json)\s*\n([\s\S]*?)```", text):
        data = _try_parse_json(m.group(1))
        if data and isinstance(data, dict) and ("tool" in data or "name" in data):
            _add_tool_call(out, data)
    # 2. Fallback: raw JSON with "tool" or "name" (some models skip the block)
    if not out:
        for m in re.finditer(r"\{[^{}]*\"(?:tool|name)\"[^{}]*\}", text):
            data = _try_parse_json(m.group(0))
            if data and isinstance(data, dict) and ("tool" in data or "name" in data):
                _add_tool_call(out, data)
                break
    return out


def _add_tool_call(out: list, data: dict) -> None:
    """Normalize and append a tool call."""
    if "tool" in data:
        out.append(dict(data))
    elif "name" in data:
        d = dict(data)
        d["tool"] = d.pop("name")
        out.append(d)


def execute_tool_calls(
    calls: list[dict],
    registry: Any,
    safety_check: Any,
    approval_callback: Any = None,
    capability_gating: bool = False,
    blast_radius_callback: Any = None,
) -> list[tuple[dict, str]]:
    """Execute each tool call. Returns [(call, result), ...]. Safety-checked.
    blast_radius_callback: (tool_name, params) -> (proceed: bool, message: str). If not proceed, require approval or block.
    """
    results = []
    for call in calls:
        name = call.get("tool") or call.get("name")
        if not name:
            results.append((call, "Error: missing tool name"))
            continue
        params = {k: v for k, v in call.items() if k not in ("tool", "name")}
        # Capability gating: restricted tools require approval
        if capability_gating and name in RESTRICTED_TOOLS:
            approved = approval_callback and approval_callback(call)
            if not approved:
                results.append((call, "[Capability Gating] This tool requires human approval. Not approved."))
                continue
        # Blast radius: pre-execution impact estimation; if exceeds threshold, require human OK
        if blast_radius_callback and name in BLAST_RADIUS_TOOLS:
            proceed, blast_msg = blast_radius_callback(name, params)
            if not proceed:
                if approval_callback:
                    call_with_reason = dict(call)
                    call_with_reason["_blast_radius_message"] = blast_msg
                    approved = approval_callback(call_with_reason)
                    if not approved:
                        results.append((call, f"[Blast Radius] {blast_msg} Human approval not granted."))
                        continue
                else:
                    results.append((call, f"[Blast Radius] {blast_msg} Pause for human approval (no callback set)."))
                    continue
        # Safety check on tool name and params
        action_str = f"tool={name} params={json.dumps(params)}"
        allowed, reason = safety_check(action_str, action_str)
        if not allowed:
            results.append((call, f"[Safety] Blocked: {reason}"))
            continue
        result = registry.execute(name, **params)
        results.append((call, result))
    return results


def format_tool_results(results: list[tuple[dict, str]]) -> str:
    """Format tool results for feeding back to LLM."""
    parts = []
    for call, result in results:
        tool = call.get("tool", call.get("name", "?"))
        parts.append(f"Tool {tool} returned: {result}")
    return "\n\n".join(parts)
