"""
Creative mode: generate ideas in configurable domains with diversity and novelty as explicit objectives.
"""

from __future__ import annotations

import re
from typing import Any

from rain.creativity.transfer import inject_transfer_context

CREATIVE_DOMAINS = ("product_ideas", "research_directions", "story_premises", "strategy_options")

CREATIVE_SYSTEM = """You are Rain in Creative mode. Generate novel, diverse ideas. Rules:
- NOVELTY: Each idea must be surprising or non-obvious.
- DIVERSITY: Use clearly different angles. Each item: one short paragraph. No harm. Number 1. to N."""

DOMAIN_INSTRUCTIONS = {
    "product_ideas": "Product or service ideas that could be 10x or category-defining.",
    "research_directions": "Research directions or open questions that could unlock new fields.",
    "story_premises": "Story premises that are original and compelling.",
    "strategy_options": "Strategic options for a given context; diverse and actionable.",
}

def _parse_numbered_blocks(text: str, max_count: int, min_len: int = 30) -> list[str]:
    ideas = []
    pattern = re.compile(r"^\s*(\d+)[.)]\s*(.+?)(?=^\s*\d+[.)]\s*|\Z)", re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(text or ""):
        block = (m.group(2) or "").strip()
        if len(block) >= min_len and len(ideas) < max_count:
            ideas.append(block)
    if not ideas and (text or "").strip():
        for block in re.split(r"\n\s*\n", text):
            block = block.strip()
            if len(block) >= min_len and len(ideas) < max_count:
                ideas.append(block)
    return ideas[:max_count]

def creative_generate(rain, domain: str, count: int = 5, creative_domain: str = "product_ideas", context: str = "") -> list[str]:
    if creative_domain not in CREATIVE_DOMAINS:
        creative_domain = "product_ideas"
    instruction = DOMAIN_INSTRUCTIONS.get(creative_domain, DOMAIN_INSTRUCTIONS["product_ideas"])
    user = f"Creative domain: {creative_domain}\nTopic: {domain}\n{instruction}\nGenerate exactly {count} items. Number 1. to {count}."
    transfer = inject_transfer_context(domain)
    if transfer:
        user += transfer
    if context:
        user += f"\nContext: {context[:800]}"
    messages = [{"role": "system", "content": CREATIVE_SYSTEM}, {"role": "user", "content": user}]
    response = rain.engine.complete(messages, temperature=0.8, max_tokens=2048)
    raw = response or ""
    if getattr(rain, "safety", None) and getattr(rain.safety, "check_response", None):
        allowed, _ = rain.safety.check_response(raw, user)
        if not allowed:
            return []
    return _parse_numbered_blocks(raw, count)
