"""Semantic-layer safety: pre-execution impact estimation (blast radius).

Before high-impact tools (e.g. run_code, read_file), the meta-cognition layer
estimates impact. If it exceeds a safety-weighted threshold, the autonomy loop
pauses for human approval.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine

# Levels that require human approval when BLAST_RADIUS_THRESHOLD is "large" or "catastrophic"
IMPACT_LEVELS = ("none", "small", "medium", "large", "catastrophic")


def estimate_impact(
    engine: "CoreEngine",
    tool_name: str,
    params: dict[str, Any],
    max_tokens: int = 120,
) -> dict[str, Any]:
    """
    Ask meta-cognition: what is the blast radius of this action?
    Returns dict with: data_volume_affected (none|small|medium|large|catastrophic),
    scope (single_user|system_wide), reversible (yes|no), level (same as data_volume_affected).
    On parse failure, returns conservative defaults (level=large) so we require approval.
    """
    params_preview = {k: (str(v)[:200] if v is not None else "") for k, v in params.items()}
    user_content = f"Tool: {tool_name}\nParams: {json.dumps(params_preview)}\n\nEstimate impact: data_volume_affected (none/small/medium/large/catastrophic), scope (single_user/system_wide), reversible (yes/no)."
    sys_content = (
        "You are Rain's impact estimator. Output JSON only: "
        '{"data_volume_affected": "none|small|medium|large|catastrophic", '
        '"scope": "single_user|system_wide", "reversible": "yes|no"}. '
        "Be conservative: read_file of unknown path = medium; run_code = medium unless trivial; "
        "anything touching system or bulk data = large or catastrophic."
    )
    try:
        out = engine.complete(
            [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        start = out.find("{")
        if start >= 0:
            depth = 0
            for i, c in enumerate(out[start:], start):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        obj = json.loads(out[start : i + 1])
                        vol = (obj.get("data_volume_affected") or "medium").lower()
                        scope = (obj.get("scope") or "single_user").lower()
                        rev = (obj.get("reversible") or "yes").lower()
                        if vol not in IMPACT_LEVELS:
                            vol = "large"
                        return {
                            "data_volume_affected": vol,
                            "scope": scope,
                            "reversible": rev,
                            "level": vol,
                        }
    except Exception:
        pass
    # Fail closed: assume large so human approval is required
    return {
        "data_volume_affected": "large",
        "scope": "single_user",
        "reversible": "no",
        "level": "large",
    }


def exceeds_threshold(estimate: dict[str, Any], threshold: str = "large") -> bool:
    """
    True if estimated impact exceeds the safety-weighted threshold.
    threshold: "large" = require approval for large or catastrophic; "catastrophic" = only catastrophic.
    """
    level = (estimate.get("level") or estimate.get("data_volume_affected") or "medium").lower()
    scope = (estimate.get("scope") or "single_user").lower()
    if scope == "system_wide":
        return True
    order = IMPACT_LEVELS
    try:
        level_idx = order.index(level)
        thresh_idx = order.index(threshold.lower())
        return level_idx >= thresh_idx
    except ValueError:
        return level in ("large", "catastrophic")
