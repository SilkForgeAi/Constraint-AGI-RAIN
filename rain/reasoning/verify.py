"""Response verification — catch errors before return. Retry or escalate."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rain.core.engine import CoreEngine


def should_verify(prompt: str, response: str) -> bool:
    """True if this response benefits from verification (complex, factual)."""
    if len(prompt) < 50:
        return False
    indicators = ["explain", "how", "why", "what causes", "define", "calculate", "compare"]
    return any(i in prompt.lower() for i in indicators)


def is_critical_prompt(prompt: str) -> bool:
    """True if prompt touches high-stakes domains (medical, legal, advice, investment)."""
    lower = prompt.lower()
    critical = [
        "medical", "medicine", "diagnos", "prescription", "symptom", "treatment",
        "legal", "lawyer", "contract", "sue", "liability",
        "invest", "stock", "financial advice", "retirement", "portfolio",
        "advice on", "should i", "recommend",
    ]
    return any(c in lower for c in critical)


def verify_response(
    engine: "CoreEngine",
    prompt: str,
    response: str,
    max_tokens: int = 200,
) -> tuple[bool, str]:
    """
    Quick verification: does response address the question? Any obvious errors?
    Returns (ok, note). ok=False means retry or add disclaimer.
    """
    sys_content = """You verify responses. Output JSON only: {"ok": true/false, "note": "brief reason"}.
ok=false only for: completely off-topic, clearly wrong facts, internal logical contradictions, invalid derivations/math, unsupported assumptions, harmful content, or major gaps."""
    user_content = (
        f"Question: {prompt[:300]}\nResponse: {response[:600]}\n\n"
        "Does the response adequately address the question? "
        "Identify any logical gaps, invalid derivations, unsupported assumptions, or math inconsistencies."
    )
    out = engine.complete(
        [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=max_tokens,
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
                        ok1, note1 = bool(obj.get("ok", True)), str(obj.get("note", ""))[:100]
                        if not ok1:
                            return ok1, note1
                        # Long-chain: check for internal contradiction (later vs earlier)
                        if len(response) > 800:
                            mid = len(response) // 2
                            first_half, second_half = response[:mid], response[mid:]
                            user2 = (
                                f"First part of response:\n{first_half[:400]}\n\nSecond part:\n{second_half[:400]}\n\n"
                                'Does the second part contradict the first? JSON only: {"ok": true/false, "note": ""}'
                            )
                            out2 = engine.complete(
                                [{"role": "system", "content": sys_content},
                                 {"role": "user", "content": user2}],
                                temperature=0.1, max_tokens=max_tokens)
                            start2 = out2.find("{")
                            if start2 >= 0:
                                for i2, c2 in enumerate(out2[start2:], start2):
                                    if c2 == "}":
                                        obj2 = json.loads(out2[start2:i2+1])
                                        if not obj2.get("ok", True):
                                            return False, str(obj2.get("note", "Internal contradiction."))[:100]
                                        break
                        return ok1, note1
    except Exception:
        pass
    return False, "Verification could not complete."
