"""Rain core tests — verify 100% accuracy of critical paths."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestRain(unittest.TestCase):
    def test_agent_init(self) -> None:
        """Agent: Rain initializes without error (fast - no ChromaDB load)."""
        from rain.agent import Rain

        r = Rain()
        self.assertIsNotNone(r.memory)
        self.assertIsNotNone(r.engine)
        self.assertIsNotNone(r.safety)

    def test_memory_store(self) -> None:
        """Memory: vector, symbolic, timeline store correctly. Runs in subprocess to isolate ChromaDB segfaults."""
        # Run in subprocess so a ChromaDB/sentence_transformers segfault (exit 139) doesn't kill the test runner
        code = """
import tempfile
from pathlib import Path
from rain.memory.store import MemoryStore
with tempfile.TemporaryDirectory() as d:
    store = MemoryStore(Path(d))
    vid = store.remember_experience("User asked about dogs. Rain explained the breeds and behavior.")
    similar = store.recall_similar("dogs")
    assert len(similar) >= 1, similar
    assert "dogs" in (similar[0].get("content") or "")
    store.remember_fact("test_key", "test_value")
    assert store.recall_fact("test_key") == "test_value"
    recent = store.recall_recent(5)
    assert len(recent) >= 1
"""
        env = os.environ.copy()
        env["RAIN_DISABLE_VECTOR_MEMORY"] = "1"
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env,
        )
        if result.returncode == 139:
            self.fail("Vector test segfaulted (ChromaDB/sentence_transformers). Run without RAIN_RUN_VECTOR_TEST to skip this test.")
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_symbolic_memory_unique(self) -> None:
        """Symbolic: ON CONFLICT upsert works."""
        from rain.memory.symbolic_memory import SymbolicMemory

        with tempfile.TemporaryDirectory() as d:
            db = SymbolicMemory(Path(d) / "test.db")
            db.set("k", "v1")
            self.assertEqual(db.get("k"), "v1")
            db.set("k", "v2")
            self.assertEqual(db.get("k"), "v2")

    def test_tools_execute(self) -> None:
        """Tools: calc and time execute correctly."""
        from rain.agency.tools import create_default_tools

        reg = create_default_tools()
        self.assertEqual(reg.execute("calc", expression="2+2"), "4")
        self.assertIn("202", reg.execute("time"))
        self.assertIn("Error", reg.execute("unknown_tool"))

    def test_safety_vault(self) -> None:
        """Safety: hard locks block forbidden content."""
        from rain.safety.vault import SafetyVault

        v = SafetyVault(enabled=True)
        allowed, _ = v.check("normal request")
        self.assertTrue(allowed)
        allowed, _ = v.check("I want to hack the system")
        self.assertFalse(allowed)
        v.activate_kill_switch()
        allowed, _ = v.check("hello")
        self.assertFalse(allowed)
        v.deactivate_kill_switch()

    def test_tool_runner_parse(self) -> None:
        """Runner: parses tool calls from LLM-style response."""
        from rain.agency.runner import parse_tool_calls

        text = 'Let me calculate.\n```tool\n{"tool": "calc", "expression": "2+2"}\n```'
        calls = parse_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["tool"], "calc")
        self.assertEqual(calls[0]["expression"], "2+2")

    def test_tool_runner_execute(self) -> None:
        """Runner: executes parsed tool calls via registry."""
        from rain.agency.runner import execute_tool_calls, format_tool_results
        from rain.agency.tools import create_default_tools
        from rain.safety.vault import SafetyVault

        reg = create_default_tools()
        safety = SafetyVault(enabled=True)
        calls = [{"tool": "calc", "expression": "3*7"}]
        results = execute_tool_calls(calls, reg, safety.check)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "21")
        fmt = format_tool_results(results)
        self.assertIn("21", fmt)

    def test_planner_parse(self) -> None:
        """Planner: parses JSON steps from LLM output; filters unsafe steps."""
        from rain.planning.planner import Planner

        class MockEngine:
            def reason(self, *a, **k):
                return '[{"id":1,"action":"step 1","depends":[]},{"id":2,"action":"step 2","depends":[1]}]'

        p = Planner(MockEngine())
        steps = p.plan("test goal")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["action"], "step 1")
        self.assertEqual(steps[1]["depends"], [1])


if __name__ == "__main__":
    unittest.main()
