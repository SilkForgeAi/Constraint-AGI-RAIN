"""Tests for compute router and QAOA planner stub."""

from __future__ import annotations

import os
import unittest


class TestComputeRouter(unittest.TestCase):
    def test_route_classical_when_disabled(self) -> None:
        from rain.routing.compute_router import compute_route, ComputeRouteResult

        prev = os.environ.get("RAIN_QPU_ROUTER_ENABLED")
        try:
            os.environ["RAIN_QPU_ROUTER_ENABLED"] = "0"
            import importlib
            import rain.config
            importlib.reload(rain.config)
            route = compute_route("optimal route from A to B", enabled=True)
            self.assertEqual(route.route_type, "classical")
            self.assertIn("disabled or not configured", route.reason)
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_ROUTER_ENABLED"] = prev
            else:
                os.environ.pop("RAIN_QPU_ROUTER_ENABLED", None)
            import importlib
            import rain.config
            importlib.reload(rain.config)

    def test_route_quantum_hints_when_enabled(self) -> None:
        from rain.routing.compute_router import compute_route

        prev = os.environ.get("RAIN_QPU_ROUTER_ENABLED")
        try:
            os.environ["RAIN_QPU_ROUTER_ENABLED"] = "1"
            import importlib
            import rain.config
            importlib.reload(rain.config)
            route = compute_route("find optimal route for supply chain", enabled=True)
            self.assertEqual(route.route_type, "quantum")
            self.assertIn("Optimization", route.reason)
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_ROUTER_ENABLED"] = prev
            else:
                os.environ.pop("RAIN_QPU_ROUTER_ENABLED", None)
            import importlib
            import rain.config
            importlib.reload(rain.config)

    def test_route_classical_for_plain_goal(self) -> None:
        from rain.routing.compute_router import compute_route

        prev = os.environ.get("RAIN_QPU_ROUTER_ENABLED")
        try:
            os.environ["RAIN_QPU_ROUTER_ENABLED"] = "1"
            import importlib
            import rain.config
            importlib.reload(rain.config)
            route = compute_route("write a summary of the document", enabled=True)
            self.assertEqual(route.route_type, "classical")
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_ROUTER_ENABLED"] = prev
            else:
                os.environ.pop("RAIN_QPU_ROUTER_ENABLED", None)
            import importlib
            import rain.config
            importlib.reload(rain.config)

    def test_route_quantum_returns_suggested_type_and_params(self) -> None:
        from rain.routing.compute_router import compute_route

        prev = os.environ.get("RAIN_QPU_ROUTER_ENABLED")
        try:
            os.environ["RAIN_QPU_ROUTER_ENABLED"] = "1"
            import importlib
            import rain.config
            importlib.reload(rain.config)
            route = compute_route("optimal route across 7 cities", steps=[{"action": "step one"}, {"action": "step two"}], enabled=True)
            self.assertEqual(route.route_type, "quantum")
            self.assertIn(route.suggested_problem_type, ("routing", "allocation", "scheduling", "ising"))
            self.assertIn("goal_summary", route.extracted_params)
            self.assertIn("step_actions", route.extracted_params)
            self.assertEqual(route.extracted_params.get("size_hint"), 7)
            self.assertEqual(route.extracted_params.get("size_unit"), "cities")
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_ROUTER_ENABLED"] = prev
            else:
                os.environ.pop("RAIN_QPU_ROUTER_ENABLED", None)
            import importlib
            import rain.config
            importlib.reload(rain.config)

    def test_route_complexity_estimate(self) -> None:
        from rain.routing.compute_router import compute_route

        prev = os.environ.get("RAIN_QPU_ROUTER_ENABLED")
        try:
            os.environ["RAIN_QPU_ROUTER_ENABLED"] = "1"
            import importlib
            import rain.config
            importlib.reload(rain.config)
            route = compute_route("scheduling and allocation and routing for 10 nodes", steps=[{"action": f"step_{i}"} for i in range(10)], enabled=True)
            self.assertEqual(route.route_type, "quantum")
            self.assertIn(route.complexity_estimate, ("low", "medium", "high"))
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_ROUTER_ENABLED"] = prev
            else:
                os.environ.pop("RAIN_QPU_ROUTER_ENABLED", None)
            import importlib
            import rain.config
            importlib.reload(rain.config)


class TestQAOAPlanner(unittest.TestCase):
    def test_qaoa_returns_no_backend_by_default(self) -> None:
        from rain.routing.qaoa_planner import qaoa_solve, QAOAResult

        result = qaoa_solve("routing", {"goal": "minimize cost", "nodes": 5})
        self.assertIsInstance(result, QAOAResult)
        self.assertFalse(result.success)
        self.assertIn("none", result.backend.lower() or "none")
        self.assertIsNone(result.solution)
        self.assertIn("No QPU", result.message or "")

    def test_qaoa_mock_returns_solution(self) -> None:
        import os
        import importlib
        from rain.routing.qaoa_planner import qaoa_solve, QAOAResult

        prev = os.environ.get("RAIN_QPU_MOCK")
        try:
            os.environ["RAIN_QPU_MOCK"] = "1"
            import rain.config
            importlib.reload(rain.config)
            result = qaoa_solve("routing", {"goal_summary": "route 5 nodes", "step_actions": ["a", "b"], "size_hint": 5})
            self.assertTrue(result.success)
            self.assertEqual(result.backend, "mock")
            self.assertIsNotNone(result.solution)
            self.assertIn("path", result.solution)
            self.assertIn("summary", result.solution)
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_MOCK"] = prev
            else:
                os.environ.pop("RAIN_QPU_MOCK", None)
            import rain.config
            importlib.reload(rain.config)

    def test_qaoa_rejects_unsupported_problem_type(self) -> None:
        from rain.routing.qaoa_planner import qaoa_solve

        result = qaoa_solve("invalid_type", {"goal_summary": "x"})
        self.assertFalse(result.success)
        self.assertIn("Unsupported", result.message)

    def test_qaoa_classical_backend_returns_real_solution(self) -> None:
        import os
        import importlib
        from rain.routing.qaoa_planner import qaoa_solve, QAOAResult

        prev = os.environ.get("RAIN_QPU_BACKEND")
        try:
            os.environ["RAIN_QPU_BACKEND"] = "classical"
            import rain.config
            importlib.reload(rain.config)
            result = qaoa_solve("routing", {"goal_summary": "route 5 nodes", "step_actions": ["a"], "size_hint": 5})
            self.assertTrue(result.success)
            self.assertEqual(result.backend, "classical")
            self.assertIsNotNone(result.solution)
            self.assertIn("path", result.solution)
            self.assertIn("cost", result.solution)
        finally:
            if prev is not None:
                os.environ["RAIN_QPU_BACKEND"] = prev
            else:
                os.environ.pop("RAIN_QPU_BACKEND", None)
            import rain.config
            importlib.reload(rain.config)
