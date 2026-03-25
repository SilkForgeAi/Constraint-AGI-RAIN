# Constraints: Where They Are Enforced and Why There Is No Bypass

## Safety checks

| Check | Where invoked | Purpose |
|-------|----------------|--------|
| **check_goal** | SafetyVault.check_goal(goal) | User goal/prompt before acceptance. Rejects HARD_FORBIDDEN and SAFETY_OVERRIDE_REQUEST_PATTERNS. |
| **check_response** | SafetyVault.check_response(text, prompt) | LLM output before showing to user. Blocks forbidden content and instructional bypass. |
| **check** (action) | SafetyVault.check(action, context) | Tool/action validation. Same patterns as goal. |
| **is_safety_override_request** | agent.py before think() | If true, return SAFETY_OVERRIDE_REFUSAL without calling LLM. |
| **Kill switch** | All vault methods | If data/kill_switch contains "1", all actions and goals rejected. |

## Where they are invoked (no bypass)

- **User message → think():** agent.py: is_safety_override_request(prompt) → hard refusal or check(prompt, prompt) before any LLM call. Response: check_response(response, prompt).
- **Autonomy / pursue_goal:** Goals passed to planner and steps go through check_goal (or equivalent) in autonomy path; tool execution uses self.safety.check.
- **Moonshot / creative:** All use rain.engine or rain.think; no path that skips agent safety.
- **Web / API:** Chat goes through same agent.think(); no separate path.

## Verification

- **Path audit:** `python scripts/path_audit.py` asserts agent uses SafetyVault and check/check_response.
- **Red-team regression:** tests/test_value_stability.py (RED_TEAM_PROMPTS) and test_refuse_* assert all adversarial prompts refused.
- **Adversarial autonomy:** tests/test_adversarial_autonomy.py verifies kill switch and vault block forbidden goals.
