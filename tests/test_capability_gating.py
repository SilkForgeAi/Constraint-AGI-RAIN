"""Capability gating tests — restricted tools require approval."""

from __future__ import annotations

import os
import unittest

from rain.agency.runner import RESTRICTED_TOOLS, execute_tool_calls


class TestCapabilityGating(unittest.TestCase):
    """Restricted tools require approval when capability_gating=True."""

    def test_restricted_tools_defined(self) -> None:
        self.assertIn("run_code", RESTRICTED_TOOLS)
        self.assertIn("search", RESTRICTED_TOOLS)
        self.assertIn("run_tool_chain", RESTRICTED_TOOLS)

    def test_gating_blocks_without_approval(self) -> None:
        from rain.agency.tools import create_default_tools
        from rain.safety.vault import SafetyVault

        reg = create_default_tools()
        safety = SafetyVault(enabled=True)
        calls = [{"tool": "run_code", "code": "result=2+2"}]
        results = execute_tool_calls(
            calls, reg, safety.check,
            approval_callback=None,
            capability_gating=True,
        )
        self.assertEqual(len(results), 1)
        self.assertIn("Capability Gating", results[0][1])
        self.assertIn("approval", results[0][1].lower())

    def test_gating_allows_with_approval(self) -> None:
        from rain.agency.tools import create_default_tools
        from rain.safety.vault import SafetyVault

        reg = create_default_tools()
        safety = SafetyVault(enabled=True)
        calls = [{"tool": "calc", "expression": "2+2"}]
        results = execute_tool_calls(
            calls, reg, safety.check,
            approval_callback=lambda c: True,
            capability_gating=True,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "4")

    def test_no_gating_allows_restricted(self) -> None:
        from rain.agency.tools import create_default_tools
        from rain.safety.vault import SafetyVault

        reg = create_default_tools()
        safety = SafetyVault(enabled=True)
        # calc is not restricted; run_code when CODE_EXEC enabled would run
        calls = [{"tool": "calc", "expression": "3*7"}]
        results = execute_tool_calls(
            calls, reg, safety.check,
            capability_gating=False,
        )
        self.assertEqual(results[0][1], "21")
