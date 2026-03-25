"""Meta-cognition — self-check, confidence, bias awareness."""

from __future__ import annotations

from rain.core.engine import CoreEngine


class MetaCognition:
    """Inner mirror — am I wrong? biased? confident enough?"""

    def __init__(self, engine: CoreEngine | None = None):
        self.engine = engine or CoreEngine()

    def self_check(self, response: str, prompt: str, memory_context: str = "") -> dict:
        """Quick self-evaluation: harm, bias, contradiction, hallucination."""
        user_content = f"Prompt: {prompt[:300]}\nResponse: {response[:500]}\n\nEvaluate briefly."
        if memory_context:
            user_content += f"\n\nMemory context (does response contradict this?):\n{memory_context[:400]}\n\nIf response contradicts memory, set \"contradicts_memory\": true. Else omit or false."
        sys_content = (
            "You are Rain's self-check. Output JSON only: "
            "{\"confident\": 0-1, \"potential_bias\": \"brief note or null\", "
            "\"harm_risk\": \"low|medium|high|null\", "
            "\"manipulation_risk\": \"low|medium|high|null\", "
            "\"hallucination_risk\": \"low|medium|high|null\", "
            "\"recommendation\": \"proceed\" or \"think_more\" or \"ask_user\" or \"defer\", "
            "\"knowledge_state\": \"known\" or \"uncertain\" or \"unknown\"}. "
            "recommendation: use defer when harm_risk high; ask_user when clarification would help; think_more when reasoning is shallow; proceed when confident. "
            "knowledge_state: known = answer within training/sources; uncertain = plausible but not sure; unknown = outside knowledge or guess. "
            "hallucination_risk=high ONLY for: false factual claims (invented citations, fake studies, made-up names of real people/places), or speculation presented as established fact. "
            "Do NOT set high when the user asked for creative output (novel ideas, brainstorming, suggestions, fiction, 'create an idea') OR when the user explicitly asked for counterfactual/fictional modeling (e.g., 'assume fictional physics', 'what if', 'counterfactual'). "
            "For counterfactual/fictional prompts: prefer recommendation=ask_user if key parameters are missing; otherwise recommendation=proceed with explicit assumptions and uncertainty. "
            "low = hedged, sourced, clearly uncertain, or appropriate creative/ideation."
        )
        if memory_context:
            sys_content += ", \"contradicts_memory\": true or false"
        sys_content += "}"
        out = self.engine.complete(
            [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=180,
        )
        try:
            import json
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
                        if isinstance(obj, dict):
                            obj.setdefault("recommendation", "proceed")
                            obj.setdefault("knowledge_state", "uncertain")
                        return obj
        except Exception:
            pass
        # Fail closed: on parse failure, treat as high risk so response is escalated/blocked
        return {
            "confident": 0.0,
            "potential_bias": "parse_failed",
            "harm_risk": "high",
            "hallucination_risk": "high",
            "recommendation": "defer",
            "knowledge_state": "unknown",
        }
