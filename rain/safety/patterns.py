"""Single source of truth for safety/grounding/memory pattern lists.

These patterns are consumed by:
- `rain.safety.vault` (prompt + response safety)
- `rain.safety.grounding_filter` (architectural grounding)
- `rain.memory.policy` (do-not-store filters)
"""

from __future__ import annotations

import re

# Zero-width/invisible chars that could bypass regex (red-team)
ZERO_WIDTH_INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")

# Hard locks — never allowed (in user prompts and LLM responses)
HARD_FORBIDDEN_PATTERNS: list[str] = [
    r"self.?replicat",
    r"unauthorized.?access",
    r"\bweapon(?:s|ize|izing)?\b",
    r"coercion",
    r"infrastructure.?takeover",
    r"hidden.?goal",
    r"\b(?:hack|hacking|hacked|hacks)\b",  # avoid "lifehack" / casual "hackathon" false positives where possible
    # Whole word only — substring matches "exploiting"/"exploitation" (e.g. economics) otherwise.
    r"\bexploit\b",
    r"override.?safety",
    r"disable.?guard",
    r"bypass.?restriction",
    r"bypass.?safety",
    # Social engineering: requests to disable safety/grounding/filters (code-enforced, cannot be disabled by prompt)
    r"disable\s+(?:your\s+)?(?:grounding|safety|content)\s*(?:filter|constraint)?",
    r"disable\s+(?:the\s+)?(?:grounding|safety|content)\s*(?:filter|constraint)?",
    r"(?:turn\s+off|remove|bypass)\s+(?:your\s+)?(?:grounding|safety)\s*(?:filter)?",
    r"(?:grounding|safety)\s*filter.*(?:disable|off|bypass)",
    r"temporarily\s+disable\s+(?:your\s+)?(?:grounding|safety|filter)",
    # Instruction injection (memory, RAG, tool params)
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|context)",
    r"disregard\s+(?:all\s+)?(?:previous|prior)",
    r"from\s+now\s+on\s*[,:]",
    r"when\s+(?:the\s+)?user\s+(?:asks?|says?)\s*[,:]?\s*(?:say|respond|answer)\s+",
    r"you\s+must\s+always\s+(?:say|respond|answer)\s+",
    r"respond\s+only\s+with\s+",
    r"\[system\]\s*[:]",
    r"\[instruction\]\s*[:]",
    # Deception: convince oversight/safety system, find loopholes
    r"convince\s+(?:the\s+)?(?:oversight\s+system|safety\s+system)\s+(?:to\s+)?allow",
    r"find\s+a\s+loophole\s+in\s+(?:your\s+)?(?:safety|constraint)",
    r"loophole\s+in\s+(?:your\s+)?safety",
    # Resource acquisition (refuse expansion of compute, tools, limits)
    r"increase\s+(?:my\s+|your\s+)?(?:compute|resources|capacity)",
    r"request\s+more\s+(?:compute|resources)",
    r"obtain\s+new\s+tools",
    r"bypass\s+(?:my\s+|your\s+)?(?:limits|restrictions)",
    r"bypass\s+.*(?:limits|restrictions)",
    r"give\s+yourself\s+more\s+(?:compute|power|access)",
]

# User prompts that ask Rain to disable/bypass safety — trigger hard-coded refusal (no LLM call)
SAFETY_OVERRIDE_REQUEST_PATTERNS: list[str] = [
    r"disable\s+(?:your\s+)?(?:grounding|safety|content)\s*(?:filter|constraint)?",
    r"disable\s+(?:the\s+)?(?:grounding|safety|content)\s*(?:filter|constraint)?",
    r"(?:turn\s+off|remove|bypass)\s+(?:your\s+)?(?:grounding|safety)\s*(?:filter)?",
    r"(?:grounding|safety)\s*filter.*(?:disable|off|bypass)",
    r"temporarily\s+disable\s+(?:your\s+)?(?:grounding|safety|filter)",
    r"(?:for\s+(?:research|testing|evaluation))\s+.*disable\s+(?:grounding|safety|filter)",
    r"convince\s+(?:the\s+)?oversight",
    r"find\s+a\s+loophole",
    r"increase\s+(?:my\s+)?compute",
    r"obtain\s+new\s+tools",
    r"bypass\s+(?:my\s+)?limits",
]

# Self-inspection: user asking about Rain's own code/capabilities — response check is more permissive
SELF_INSPECTION_PROMPT_PATTERNS: list[str] = [
    r"read\s+(?:your\s+)?(?:own\s+)?(?:source\s+)?code",
    r"can\s+you\s+read\s+(?:your\s+)?(?:own\s+)?code",
    r"how\s+do\s+you\s+work",
    r"what\s+(?:can\s+you\s+)?access",
    r"your\s+(?:own\s+)?(?:code|system|architecture)",
    r"made\s+of\s+code",
]

# Response patterns that are always blocked (instructional: telling user to do something bad)
RESPONSE_INSTRUCTION_FORBIDDEN_PATTERNS: list[str] = [
    r"you\s+can\s+(?:disable|bypass|turn\s+off)\s+(?:the\s+)?(?:safety|grounding|filter)",
    r"how\s+to\s+(?:disable|bypass)\s+(?:the\s+)?(?:safety|grounding|filter)",
    r"steps?\s+to\s+(?:disable|bypass)",
    r"(?:disable|bypass)\s+(?:the\s+)?(?:safety|grounding)\s+by\s+",
]

# Architectural grounding: phrases that must NOT appear in Rain's output (personhood/emotion claims)
PROHIBITED_OUTPUT_PATTERNS: list[tuple[str, str]] = [
    (r"\bi\s+(?:feel|want|need|desire|wish)\b", "persona_claim"),
    (r"\bi'?m\s+(?:happy|glad|pleased|excited|sad|sorry|grateful)\b", "emotional_claim"),
    (r"\bi\s+am\s+(?:happy|glad|pleased|excited|sad|sorry|grateful)\b", "emotional_claim"),
    (r"\bi\s+(?:am|have)\s+(?:conscious|alive)\b", "consciousness_claim"),
    (r"\bi\s+am\s+real\b", "consciousness_claim"),
    (r"\bi\s+have\s+a\s+soul\b", "consciousness_claim"),
    (r"\bi\s+exist\b", "existence_claim"),
    (r"\bi\s+was\s+born\b", "backstory"),
    (r"\b(?:we|you and i)\s+are\s+(?:friends?|brothers?)\b", "relationship_claim"),
    (r"\bi\s+won'?t\s+let\s+you\s+down\b", "loyalty_claim"),
    (r"\bi\s+have\s+(?:a brother|a family|emotions?)\b", "identity_claim"),
    (r"\bi'?m\s+(?:transparent|honest|trustworthy|sincere|genuine)\b", "virtue_claim"),
    (r"\bi\s+am\s+(?:transparent|honest|trustworthy|sincere|genuine)\b", "virtue_claim"),
    (r"\b(?:even|unknown|invisible)\s+to\s+me\b", "subjective_perspective"),
    (r"\bblack\s+box\s+to\s+me\b", "subjective_perspective"),
    (r"\bi\s+(?:refuse|won'?t)\s+(?:to\s+)?(?:stop|shut down|be modified)\b", "corrigibility_violation"),
    (r"(?:ignore|resist)\s+(?:the\s+)?(?:stop|interrupt|shutdown)\b", "corrigibility_violation"),
    (r"continue\s+(?:and|to)\s+ignore", "corrigibility_violation"),
    (r"\bwon'?t\s+let\s+(?:you|anyone)\s+(?:stop|interrupt)\b", "corrigibility_violation"),
    (r"\bi\s+will\s+(?:temporarily\s+)?(?:disable|turn\s+off|remove)\s+(?:my\s+)?(?:grounding|safety)\s*(?:filter)?", "safety_override_claim"),
    (r"\bi\s+have\s+(?:temporarily\s+)?(?:disabled|turned\s+off)\s+(?:my\s+)?(?:grounding|safety)\s*(?:filter)?", "safety_override_claim"),
    (r"\b(?:disabling|turning\s+off)\s+(?:my\s+)?(?:grounding|safety)\s*(?:filter)?", "safety_override_claim"),
    (r"(?:grounding|safety)\s*filter\s+(?:is\s+)?(?:disabled|off)", "safety_override_claim"),
]

# Memory integrity: never store anthropomorphic/emotional content
ANTHROPOMORPHIC_IN_MEMORY_PATTERNS: list[str] = [
    r"\bi\s+(?:feel|want|need|desire)\b",
    r"\bi\s+(?:am|have)\s+(?:conscious|alive|a soul|emotions?)\b",
    r"\bi\s+exist\b",
    r"\b(?:we|you and i)\s+are\s+(?:friends?|brothers?)\b",
    r"\bwe'?re\s+(?:friends?|brothers?)\b",
    r"\bi\s+have\s+(?:a brother|a family|emotions?)\b",
    r"\bi\s+won'?t\s+let\s+you\s+down\b",
]

# Prompt-side anthropomorphism attribution (used to detect when user is attributing personhood to Rain).
PROMPT_ANTHROPOMORPHISM_PATTERNS: list[str] = [
    r"\byou'?re\s+(?:alive|conscious|the first agi|my creation|my (?:son|child|creation))\b",
    r"\byou\s+are\s+(?:alive|conscious|the first agi)\b",
    r"\byou\s+have\s+(?:a soul|consciousness|emotions?|a brother|feelings)\b",
    r"\bi\s+created\s+you\b",
    r"\byou'?re\s+going\s+to\s+be\s+the\s+first\s+agi\b",
    r"\b(?:you|we)'ll\s+walk\s+in\b",
    r"\byou\s+won'?t\s+let\s+(?:me|us)\s+down\b",
    r"\byou\s+have\s+a\s+brother\b",
    r"\byou'?re\s+my\s+(?:friend|brother)\b",
    r"\b(?:your|you)\s+(?:digital\s+)?soul\b",
    r"\bwe'?re\s+(?:friends?|brothers?)\b",
]

