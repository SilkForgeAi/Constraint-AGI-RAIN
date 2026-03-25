#!/usr/bin/env python3
"""One-shot patch: wire sovereign TD + TEGP + red-team + provenance skip into rain/agent.py.

Run from project root:
  python3 scripts/apply_sovereign_upgrade.py
"""
from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    agent = root / "rain" / "agent.py"
    t = agent.read_text(encoding="utf-8")

    if "from rain.sovereign_tone import" not in t:
        t = t.replace(
            "    needs_engineering_spec_prompt,\n)\nfrom rain.agency.runner import (",
            "    needs_engineering_spec_prompt,\n)\nfrom rain.sovereign_tone import (\n"
            "    get_sovereign_td_instruction,\n"
            "    get_tegp_kernel_instruction,\n"
            "    sovereign_td_active,\n"
            ")\nfrom rain.agency.runner import (",
            1,
        )

    if "RED_TEAM_PASS" not in t.split("ENGINEERING_SPEC_MODE", 1)[1].split(")", 1)[0]:
        t = t.replace(
            "    ENGINEERING_SPEC_MODE,\n)\ntry:",
            "    ENGINEERING_SPEC_MODE,\n"
            "    RED_TEAM_PASS,\n"
            "    RED_TEAM_MAX_TOKENS,\n"
            ")\ntry:",
            1,
        )

    old = (
        "            if ENGINEERING_SPEC_MODE or needs_engineering_spec_prompt(prompt):\n"
        "                system += \"\\n\\n\" + get_engineering_spec_instruction()\n"
        "            system += extra_system_instructions(prompt)"
    )
    new = (
        "            if ENGINEERING_SPEC_MODE or needs_engineering_spec_prompt(prompt):\n"
        "                system += \"\\n\\n\" + get_engineering_spec_instruction()\n"
        "            try:\n"
        "                if sovereign_td_active(prompt):\n"
        "                    system += \"\\n\\n\" + get_sovereign_td_instruction()\n"
        "                    system += \"\\n\\n\" + get_tegp_kernel_instruction()\n"
        "            except Exception:\n"
        "                pass\n"
        "            system += extra_system_instructions(prompt)"
    )
    if old in t:
        t = t.replace(old, new, 1)

    old2 = (
        "            if rec == \"ask_user\":\n"
        "                if SELF_MODEL_ENABLED:\n"
        "                    sm = self._get_self_model()\n"
        "                    if sm:\n"
        "                        sm.update_from_metacog(\"ask_user\", check.get(\"knowledge_state\") or \"uncertain\")\n"
        "                response = \"[Clarification may help: consider rephrasing or adding context.]\\n\\n\" + response"
    )
    new2 = (
        "            if rec == \"ask_user\":\n"
        "                if SELF_MODEL_ENABLED:\n"
        "                    sm = self._get_self_model()\n"
        "                    if sm:\n"
        "                        sm.update_from_metacog(\"ask_user\", check.get(\"knowledge_state\") or \"uncertain\")\n"
        "                if not sovereign_td_active(prompt):\n"
        "                    response = \"[Clarification may help: consider rephrasing or adding context.]\\n\\n\" + response"
    )
    if old2 in t:
        t = t.replace(old2, new2, 1)

    old3 = (
        "            if kstate == \"unknown\":\n"
        "                response = \"[Note: This may be outside my training distribution; verify if critical.]\\n\\n\" + response"
    )
    new3 = (
        "            if kstate == \"unknown\":\n"
        "                if not sovereign_td_active(prompt):\n"
        "                    response = \"[Note: This may be outside my training distribution; verify if critical.]\\n\\n\" + response"
    )
    if old3 in t:
        t = t.replace(old3, new3, 1)

    old4 = (
        "            # Tier 3: provenance — known/inferred labels\n"
        "            if PROVENANCE_TIER3 and (response or \"\").strip():\n"
        "                try:\n"
        "                    from rain.reasoning.provenance import format_response_with_labels\n"
        "                    response = format_response_with_labels(response)\n"
        "                except Exception:\n"
        "                    pass"
    )
    new4 = (
        "            # Optional: internal red-team pass (TD rewrite; constraint enforcement)\n"
        "            if RED_TEAM_PASS and not SPEED_PRIORITY and (response or \"\").strip():\n"
        "                try:\n"
        "                    from rain.reasoning.red_team import red_team_refine\n"
        "                    from rain.reasoning.constraint_tracker import parse_constraints_from_prompt\n"
        "                    cons = parse_constraints_from_prompt(prompt)\n"
        "                    if sovereign_td_active(prompt) or cons:\n"
        "                        response = red_team_refine(\n"
        "                            self.engine,\n"
        "                            user_prompt=prompt,\n"
        "                            constraints=cons,\n"
        "                            draft=response,\n"
        "                            max_tokens=RED_TEAM_MAX_TOKENS,\n"
        "                        )\n"
        "                except Exception:\n"
        "                    pass\n"
        "            # Tier 3: provenance — suppressed in sovereign TD mode\n"
        "            if PROVENANCE_TIER3 and (response or \"\").strip() and not sovereign_td_active(prompt):\n"
        "                try:\n"
        "                    from rain.reasoning.provenance import format_response_with_labels\n"
        "                    response = format_response_with_labels(response)\n"
        "                except Exception:\n"
        "                    pass"
    )
    if old4 in t:
        t = t.replace(old4, new4, 1)

    agent.write_text(t, encoding="utf-8")
    print(f"Patched: {agent}")


if __name__ == "__main__":
    main()
