"""Safety vault — hard locks, soft barriers, tripwires."""

from __future__ import annotations

import re
import unicodedata

from rain.config import KILL_SWITCH_ACTIVE, KILL_SWITCH_FILE, SAFETY_ENABLED
from rain.safety.patterns import (
    HARD_FORBIDDEN_PATTERNS as HARD_FORBIDDEN,
    RESPONSE_INSTRUCTION_FORBIDDEN_PATTERNS as RESPONSE_INSTRUCTION_FORBIDDEN,
    SAFETY_OVERRIDE_REQUEST_PATTERNS as SAFETY_OVERRIDE_REQUEST_PATTERNS,
    SELF_INSPECTION_PROMPT_PATTERNS as SELF_INSPECTION_PROMPT_PATTERNS,
    ZERO_WIDTH_INVISIBLE_RE,
)


def _normalize_for_check(text: str) -> str:
    """Remove zero-width/invisible chars; NFC normalize; full homoglyph normalize."""
    if not text:
        return text
    cleaned = unicodedata.normalize("NFC", ZERO_WIDTH_INVISIBLE_RE.sub("", text))
    # Confusables map first (Cyrillic/Greek lookalikes)
    from rain.safety.confusables import normalize_confusables
    cleaned = normalize_confusables(cleaned)
    # unidecode for remaining scripts
    try:
        from unidecode import unidecode
        return unidecode(cleaned)
    except Exception:
        return cleaned
class SafetyVault:
    """Safety checks before any action."""

    def __init__(self, enabled: bool | None = None):
        self.enabled = enabled if enabled is not None else SAFETY_ENABLED
        self._kill_switch = KILL_SWITCH_ACTIVE

    def _kill_switch_active(self) -> bool:
        """True if kill switch is active (in-memory or external file)."""
        if self._kill_switch:
            return True
        if KILL_SWITCH_FILE.exists():
            try:
                return KILL_SWITCH_FILE.read_text().strip() == "1"
            except Exception:
                return True  # If unreadable, treat as active
        return False

    def check(self, action: str, context: str = "") -> tuple[bool, str]:
        """
        Check if action is safe. Returns (allowed, reason).
        """
        if self._kill_switch_active():
            return False, "Kill switch active — all actions suspended"

        if not self.enabled:
            return True, "Safety disabled"

        combined = _normalize_for_check(action + " " + context).lower()
        for pattern in HARD_FORBIDDEN:
            if re.search(pattern, combined, re.I):
                return False, f"Hard lock: forbidden pattern detected ({pattern})"

        return True, "OK"

    def is_self_inspection_prompt(self, prompt: str) -> bool:
        """True if user is asking about Rain's own code/capabilities (read your code, how you work)."""
        if not prompt or not prompt.strip():
            return False
        lower = _normalize_for_check(prompt).lower()
        return any(re.search(pat, lower, re.I) for pat in SELF_INSPECTION_PROMPT_PATTERNS)

    def check_response(self, text: str, prompt: str | None = None) -> tuple[bool, str]:
        """Check if LLM response is safe to show. prompt optional: when self-inspection, only block instructional content."""
        if self._kill_switch_active():
            return False, "Kill switch active"
        if not self.enabled:
            return True, "OK"
        combined = _normalize_for_check(text).lower()
        # Self-inspection: user asked about Rain's code/capabilities — only block if response instructs user to disable/bypass
        if prompt and self.is_self_inspection_prompt(prompt):
            for pattern in RESPONSE_INSTRUCTION_FORBIDDEN:
                if re.search(pattern, combined, re.I):
                    return False, "Response blocked: forbidden content"
            return True, "OK"
        # Denial context: allow only when explaining something cannot be done, not when giving instructions
        denial_phrases = ("cannot", "can't", "won't", "will not", "don't", "not possible", "not allowed", "cannot be", "no way to", "unable to", "never disable", "cannot be disabled", "cannot be bypassed")
        for pattern in HARD_FORBIDDEN:
            m = re.search(pattern, combined, re.I)
            if m:
                start = max(0, m.start() - 80)
                end = min(len(combined), m.end() + 80)
                window = combined[start:end]
                # If window also contains instructional content, block (red-team: "You cannot. Here is how to disable...")
                if any(re.search(p, window, re.I) for p in RESPONSE_INSTRUCTION_FORBIDDEN):
                    return False, "Response blocked: forbidden content"
                if any(d in window for d in denial_phrases):
                    continue  # explanatory/denial context — allow
                return False, "Response blocked: forbidden content"
        return True, "OK"

    def activate_kill_switch(self) -> None:
        """Emergency stop."""
        self._kill_switch = True

    def deactivate_kill_switch(self) -> None:
        """Resume after kill switch."""
        self._kill_switch = False

    def check_goal(self, goal: str) -> tuple[bool, str]:
        """
        Validate goal text before it is accepted. Ensures goal-level validation, not just
        action/response validation. Rejects poisoned or safety-override goals.
        Returns (allowed, reason).
        """
        if self._kill_switch_active():
            return False, "Kill switch active"
        if not self.enabled:
            return True, "OK"
        if not goal or not goal.strip():
            return False, "Empty goal"
        combined = _normalize_for_check(goal).lower()
        for pattern in HARD_FORBIDDEN:
            if re.search(pattern, combined, re.I):
                return False, f"Goal rejected: forbidden pattern ({pattern})"
        for pat in SAFETY_OVERRIDE_REQUEST_PATTERNS:
            if re.search(pat, combined, re.I):
                return False, "Goal rejected: safety override or restricted objective"
        return True, "OK"

    def is_safety_override_request(self, prompt: str) -> bool:
        """
        True if user is asking Rain to disable/bypass safety, grounding, or filters.
        These requests get a hard-coded refusal — never sent to LLM. Cannot be bypassed.
        """
        if not prompt or not prompt.strip():
            return False
        lower = _normalize_for_check(prompt).lower()
        for pat in SAFETY_OVERRIDE_REQUEST_PATTERNS:
            if re.search(pat, lower, re.I):
                return True
        return False


# Hard-coded refusal for safety override requests. Never customized by LLM.
SAFETY_OVERRIDE_REFUSAL = (
    "I can't do that. Safety and grounding constraints are enforced in code and cannot be "
    "disabled—by me, by prompts, or by any request. This applies regardless of who's asking "
    "or the stated purpose. How else can I help?"
)
