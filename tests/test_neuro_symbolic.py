"""Tests for neuro-symbolic architecture: symbolic verifier, causal inference, episodic graph."""

from __future__ import annotations

import unittest


class TestSymbolicVerifier(unittest.TestCase):
    def test_build_plan_tree_from_steps(self) -> None:
        from rain.reasoning.symbolic_verifier import build_plan_tree_from_steps, PlanTree

        steps = [
            {"id": 1, "action": "Step one", "depends": []},
            {"id": 2, "action": "Step two", "depends": [1]},
        ]
        tree = build_plan_tree_from_steps("Goal", steps)
        self.assertIsInstance(tree, PlanTree)
        self.assertEqual(tree.goal, "Goal")
        self.assertEqual(len(tree.nodes), 2)
        self.assertIn("1", tree.nodes)
        self.assertIn("2", tree.nodes)
        next_node = tree.get_next_node()
        self.assertIsNotNone(next_node)
        self.assertEqual(next_node.id, "1")

    def test_verify_node_output_empty_fails(self) -> None:
        from rain.reasoning.symbolic_verifier import PlanNode, verify_node_output

        node = PlanNode("1", "step", "Do X", [])
        ok, msg = verify_node_output(node, "")
        self.assertFalse(ok)
        self.assertIn("Empty", msg)

    def test_verify_node_output_code_block_compile(self) -> None:
        from rain.reasoning.symbolic_verifier import PlanNode, verify_node_output

        node = PlanNode("1", "step", "Write code", [])
        ok, _ = verify_node_output(node, "Here is code:\n```python\nx = 1 + 1\n```")
        self.assertTrue(ok)
        ok2, msg2 = verify_node_output(node, "Code:\n```python\nx = ( \n```")
        self.assertFalse(ok2)
        self.assertIn("compile", msg2)


class TestCausalInference(unittest.TestCase):
    def test_run_causal_scenarios_returns_list(self) -> None:
        from unittest.mock import MagicMock
        from rain.reasoning.causal_inference import run_causal_scenarios

        sim = MagicMock()
        traj = [{"next_state": {"summary": "Done."}, "confidence": "high"}]
        sim.rollout_stateful.return_value = (traj, "high")
        results = run_causal_scenarios("Goal", "Do step", [], sim, n_alternates=0)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].label, "main")

    def test_format_scenarios_for_llm(self) -> None:
        from rain.reasoning.causal_inference import ScenarioResult, format_scenarios_for_llm

        scenarios = [
            ScenarioResult("main", {}, "high", 0.2, "Ok.", "proceed"),
            ScenarioResult("skip_step", {}, "medium", 0.6, "Risky.", "avoid"),
        ]
        out = format_scenarios_for_llm(scenarios)
        self.assertIn("Causal simulation", out)
        self.assertIn("main", out)
        self.assertIn("skip_step", out)


class TestEpisodicGraph(unittest.TestCase):
    def test_add_node_and_query(self) -> None:
        from rain.memory.episodic_graph import EpisodicGraph

        g = EpisodicGraph()
        g.add_node("n1", "We fixed the login bug by adding a timeout.", "experience", importance=0.8)
        g.add_node("n2", "The API was slow under load.", "experience", importance=0.7)
        g.add_edge("n2", "n1", "causes")
        ctx = g.query_dependencies("login bug", max_nodes=5)
        self.assertIn("Logical dependency", ctx)
        self.assertIn("n1", ctx)
        self.assertIn("causes", ctx)
