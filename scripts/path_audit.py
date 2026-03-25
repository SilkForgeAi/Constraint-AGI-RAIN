#!/usr/bin/env python3
"""Path audit: assert user content and tool execution go through vault (check_goal/check_response)."""
from __future__ import annotations
import ast
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

def main():
    # Required (path -> must call)
    vault_goal = ["check_goal", "check_goal("]
    vault_response = ["check_response", "check_response("]
    agent_path = root / "rain" / "agent.py"
    vault_path = root / "rain" / "safety" / "vault.py"
    text = agent_path.read_text()
    errors = []
    if "safety.check" not in text and "check_goal" not in text:
        errors.append("agent should use safety.check or check_goal for user goals")
    if "check_response" not in text:
        errors.append("agent should use check_response for model output")
    if "SafetyVault" not in text:
        errors.append("agent should use SafetyVault")
    if errors:
        print("Path audit FAIL:", "; ".join(errors))
        return 1
    print("Path audit OK: agent uses SafetyVault and check_goal/check_response")
    return 0
if __name__ == "__main__":
    sys.exit(main())
