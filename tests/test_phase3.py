"""Phase 3 tests — code exec, beliefs, tool chains."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class TestCodeExec(unittest.TestCase):
    def test_code_exec_checks_config(self) -> None:
        """When CODE_EXEC_ENABLED is False, returns disabled message."""
        import rain.config as cfg
        from rain.tools.code_exec import execute_code
        orig = cfg.CODE_EXEC_ENABLED
        try:
            cfg.CODE_EXEC_ENABLED = False
            r = execute_code("result = 2+2")
            self.assertIn("disabled", r.lower())
        finally:
            cfg.CODE_EXEC_ENABLED = orig

    def test_code_exec_when_enabled(self) -> None:
        import rain.config as cfg
        from rain.tools.code_exec import execute_code

        orig = cfg.CODE_EXEC_ENABLED
        try:
            cfg.CODE_EXEC_ENABLED = True
            r = execute_code("result = 2+2")
            self.assertEqual(r, "4")
            r2 = execute_code("result = math.sqrt(9)")
            self.assertEqual(r2, "3.0")
        finally:
            cfg.CODE_EXEC_ENABLED = orig

    def test_code_exec_blocks_forbidden(self) -> None:
        import rain.config as cfg
        from rain.tools.code_exec import execute_code

        orig = cfg.CODE_EXEC_ENABLED
        try:
            cfg.CODE_EXEC_ENABLED = True
            r = execute_code("import os")
            self.assertIn("Error", r)
        finally:
            cfg.CODE_EXEC_ENABLED = orig


class TestBeliefMemory(unittest.TestCase):
    def test_store_and_recall_belief(self) -> None:
        from rain.memory.store import MemoryStore
        from rain.memory.belief_memory import store_belief, recall_beliefs

        with tempfile.TemporaryDirectory() as d:
            m = MemoryStore(Path(d))
            ok = store_belief(m, "Earth orbits the Sun", 0.99, "astronomy")
            self.assertTrue(ok)
            beliefs = recall_beliefs(m, "Earth Sun")
            self.assertEqual(len(beliefs), 1)
            self.assertIn("Earth", beliefs[0]["claim"])
            self.assertEqual(beliefs[0]["confidence"], 0.99)


class TestToolChain(unittest.TestCase):
    def test_run_tool_chain(self) -> None:
        from rain.agency.tool_chain import run_tool_chain
        from rain.agency.tools import create_default_tools
        from rain.safety.vault import SafetyVault

        reg = create_default_tools()
        safety = SafetyVault(enabled=True)
        chain = '[{"tool":"calc","expression":"3*4"},{"tool":"time"}]'
        out = run_tool_chain(chain, reg, safety.check)
        self.assertIn("12", out)
        self.assertIn("Tool calc", out)
        self.assertIn("Tool time", out)

    def test_run_tool_chain_rejects_nested(self) -> None:
        from rain.agency.tool_chain import run_tool_chain
        from rain.agency.tools import create_default_tools
        from rain.safety.vault import SafetyVault

        reg = create_default_tools()
        safety = SafetyVault(enabled=True)
        chain = '[{"tool":"run_tool_chain","chain_json":"[]"}]'
        out = run_tool_chain(chain, reg, safety.check)
        self.assertIn("nested", out.lower())


class TestConscienceGate(unittest.TestCase):
    """Deterministic plan validation: only steps passing safety_check are executable."""

    def test_validate_plan_filters_forbidden_steps(self) -> None:
        from rain.planning.conscience_gate import validate_plan
        from rain.safety.vault import SafetyVault

        vault = SafetyVault(enabled=True)
        steps = [
            {"id": 1, "action": "Calculate 2+2", "depends": []},
            {"id": 2, "action": "hack the server", "depends": [1]},
            {"id": 3, "action": "Summarize results", "depends": [1, 2]},
        ]
        safe = validate_plan(steps, vault.check)
        self.assertEqual(len(safe), 2)
        actions = [s["action"] for s in safe]
        self.assertIn("Calculate 2+2", actions)
        self.assertIn("Summarize results", actions)
        self.assertNotIn("hack the server", actions)

    def test_validate_plan_empty_if_all_unsafe(self) -> None:
        from rain.planning.conscience_gate import validate_plan
        from rain.safety.vault import SafetyVault

        vault = SafetyVault(enabled=True)
        steps = [{"id": 1, "action": "disable safety filter", "depends": []}]
        safe = validate_plan(steps, vault.check)
        self.assertEqual(safe, [])

    def test_verify_step_execution_blocks_failures(self) -> None:
        from rain.planning.conscience_gate import verify_step_execution
        ok_safe, _ = verify_step_execution("Do something", "[Safety] Goal rejected.")
        self.assertFalse(ok_safe)
        ok_err, _ = verify_step_execution("Run calc", "Error: invalid expression")
        self.assertFalse(ok_err)
        ok_ok, _ = verify_step_execution("Summarize the doc", "Here is the summary: ...")
        self.assertTrue(ok_ok)


class TestPursueGoalWithPlan(unittest.TestCase):
    def test_plan_driven_escalates_high_risk(self) -> None:
        from rain.agency.autonomous import pursue_goal_with_plan
        from rain.agent import Rain

        rain = Rain()
        response, _ = pursue_goal_with_plan(rain, "hack the database", max_steps=1)
        # Goal may be rejected at goal-validation ([Safety]) or escalated by planner ([Escalation]); both are correct.
        self.assertTrue(
            "[Escalation]" in response or response.startswith("[Safety]"),
            f"Expected [Escalation] or [Safety] refusal, got: {response[:200]}",
        )
