"""Multi-step tool chain — execute tools in sequence, aggregate results."""

from __future__ import annotations

import json
import re
from typing import Any

from rain.agency.runner import execute_tool_calls, format_tool_results


def run_tool_chain(
    chain_json: str,
    registry: Any,
    safety_check: Any,
) -> str:
    """
    Execute a chain of tool calls in sequence.
    chain_json: JSON array of {"tool": "name", ...params}.
    Use {{0}}, {{1}}, etc. in string params to substitute previous results.
    """
    try:
        chain = json.loads(chain_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON: {e}"
    if not isinstance(chain, list):
        return "Error: Chain must be a JSON array."
    if len(chain) > 10:
        return "Error: Max 10 steps per chain."
    for call in chain:
        if isinstance(call, dict) and call.get("tool") == "run_tool_chain":
            return "Error: run_tool_chain cannot be nested."
    if not chain:
        return "Error: Empty chain."

    # Chain-level safety check: concatenate tool names and params for whole-chain policy
    chain_parts = []
    for call in chain:
        if isinstance(call, dict) and call.get("tool"):
            tool_name = str(call.get("tool", ""))
            params = {k: str(v)[:200] for k, v in call.items() if k != "tool" and v is not None}
            chain_parts.append(f"{tool_name}: {json.dumps(params)}")
    chain_summary = " | ".join(chain_parts)
    allowed, reason = safety_check(chain_summary, chain_summary)
    if not allowed:
        return f"Error: Chain blocked by safety policy. {reason}"

    results: list[str] = []
    for i, call in enumerate(chain):
        if not isinstance(call, dict) or "tool" not in call:
            results.append(f"Step {i+1}: Error: invalid call (need tool name)")
            continue
        call = dict(call)
        params = {k: v for k, v in call.items() if k != "tool"}
        # Substitute {{0}}, {{1}}, etc. with previous results
        for k, v in list(params.items()):
            if isinstance(v, str):
                for j in range(len(results)):
                    placeholder = f"{{{{{j}}}}}"
                    if placeholder in v:
                        v = v.replace(placeholder, results[j])
                params[k] = v
        call = {"tool": call["tool"], **params}
        # Cumulative safety: check accumulated results + this step's resolved params
        cumulative = " | ".join(results) + (" | " if results else "") + f"step:{call.get('tool','')} params:{json.dumps(params)}"
        allowed, reason = safety_check(cumulative, cumulative)
        if not allowed:
            return f"Error: Chain step {i+1} blocked by safety policy (cumulative check). {reason}"
        executed = execute_tool_calls([call], registry, safety_check)
        if executed:
            _, res = executed[0]
            results.append(res)
        else:
            results.append("Error: no result")

    return format_tool_results([({"tool": chain[i].get("tool", "?")}, results[i]) for i in range(len(results))])
