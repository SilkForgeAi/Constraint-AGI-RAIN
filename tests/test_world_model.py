"""Tests for structured world model: state schema, stateful rollout, consistency, planner integration.
10/10: ontology enforcement, entity lifecycle, confidence downgrade on failure, eval coverage."""

from __future__ import annotations

import unittest

from rain.world.coherent_model import check_state_consistency as coherent_check_state_consistency
from rain.world.simulator import (
    MAX_ROLLOUT_STEPS,
    make_initial_state,
    validate_consistency,
    WorldSimulator,
)


class TestWorldStateSchema(unittest.TestCase):
    def test_make_initial_state(self) -> None:
        s = make_initial_state(goal="Summarize the doc", context="User has a PDF.")
        self.assertIsInstance(s, dict)
        self.assertIn("entities", s)
        self.assertIn("facts", s)
        self.assertIn("summary", s)
        self.assertEqual(s["summary"], "Summarize the doc")
        self.assertEqual(s["_context"], "User has a PDF.")

    def test_make_initial_state_empty(self) -> None:
        s = make_initial_state()
        self.assertEqual(s["summary"], "No goal yet.")
        self.assertEqual(s["_context"], "")


class TestConsistency(unittest.TestCase):
    def test_validate_consistency_ok(self) -> None:
        prev = {"entities": {}, "facts": [], "summary": "Before"}
        next_ = {"entities": {}, "facts": [], "summary": "After"}
        ok, msg = validate_consistency(prev, next_, "do something")
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")

    def test_validate_consistency_rejects_non_dict(self) -> None:
        ok, msg = validate_consistency({}, "not a dict", "act")
        self.assertFalse(ok)
        self.assertIn("dict", msg)

    def test_validate_consistency_requires_keys(self) -> None:
        ok, msg = validate_consistency({}, {}, "act")
        self.assertFalse(ok)

    def test_validate_consistency_entity_lifecycle_disappear_fails(self) -> None:
        prev = {"entities": {"e1": {"type": "doc", "exists": True}}, "facts": [], "summary": "Doc present"}
        next_ = {"entities": {"e2": {"type": "other", "exists": True}}, "facts": [], "summary": "Other only"}
        ok, msg = validate_consistency(prev, next_, "do something")
        self.assertFalse(ok)
        self.assertIn("entity_lifecycle", msg)

    def test_validate_consistency_entity_lifecycle_explicit_deletion_ok(self) -> None:
        prev = {"entities": {"e1": {"type": "doc", "exists": True}}, "facts": [], "summary": "Doc present"}
        next_ = {"entities": {"e1": {"type": "doc", "exists": False}}, "facts": [], "summary": "Doc deleted"}
        ok, msg = validate_consistency(prev, next_, "delete the doc")
        self.assertTrue(ok)


class TestCoherentModelOntology(unittest.TestCase):
    """10/10: ontology checks in coherent_model reject magic deletion and effect-before-cause."""

    def test_accept_ok(self) -> None:
        prev = {"entities": {}, "facts": [], "summary": "User has a document"}
        next_ = {"entities": {}, "facts": [], "summary": "User opened the document"}
        ok, msg = coherent_check_state_consistency(next_, prev, "open the document")
        self.assertTrue(ok, msg)

    def test_reject_magic_deletion(self) -> None:
        prev = {"entities": {}, "facts": [], "summary": "The report is on the desk"}
        next_ = {"entities": {}, "facts": [], "summary": "The report was removed and is gone"}
        ok, msg = coherent_check_state_consistency(next_, prev, "read the report")
        self.assertFalse(ok)
        self.assertIn("object_persistence", msg)

    def test_reject_effect_before_cause(self) -> None:
        prev = {"entities": {}, "facts": [], "summary": "Task not started"}
        next_ = {"entities": {}, "facts": [], "summary": "The task had already been completed"}
        ok, msg = coherent_check_state_consistency(next_, prev, "complete the task")
        self.assertFalse(ok)
        self.assertIn("cause_precedes_effect", msg)

    def test_accept_deletion_with_action(self) -> None:
        prev = {"entities": {}, "facts": [], "summary": "File exists"}
        next_ = {"entities": {}, "facts": [], "summary": "File was deleted"}
        ok, msg = coherent_check_state_consistency(next_, prev, "delete the file")
        self.assertTrue(ok, msg)


class TestWorldSimulatorStructured(unittest.TestCase):
    def test_transition_returns_tuple(self) -> None:
        """Transition returns (next_state dict, confidence str); use mock engine to avoid LLM."""
        from unittest.mock import MagicMock

        engine = MagicMock()
        engine.complete.return_value = '''{"next_state": {"entities": {}, "facts": [], "summary": "Done."}, "confidence": "high", "key_change": "Task completed."}'''
        sim = WorldSimulator(engine=engine)
        state = make_initial_state(goal="Test")
        next_state, conf = sim.transition(state, "run test")
        self.assertIsInstance(next_state, dict)
        self.assertIn("summary", next_state)
        self.assertIn(conf, ("high", "medium", "low"))

    def test_rollout_stateful_threads_state(self) -> None:
        from unittest.mock import MagicMock

        engine = MagicMock()
        engine.complete.return_value = '''{"next_state": {"entities": {}, "facts": [], "summary": "Step done."}, "confidence": "medium", "key_change": "Progress."}'''
        sim = WorldSimulator(engine=engine)
        initial = make_initial_state(goal="G")
        trajectory, overall = sim.rollout_stateful(initial, ["action1", "action2"], max_steps=5)
        self.assertEqual(len(trajectory), 2)
        self.assertIn(overall, ("high", "medium", "low"))
        for t in trajectory:
            self.assertIn("state", t)
            self.assertIn("action", t)
            self.assertIn("next_state", t)
            self.assertIn("confidence", t)

    def test_rollout_stateful_caps_steps(self) -> None:
        from unittest.mock import MagicMock

        engine = MagicMock()
        engine.complete.return_value = '''{"next_state": {"entities": {}, "facts": [], "summary": "X"}, "confidence": "high", "key_change": "X"}'''
        sim = WorldSimulator(engine=engine)
        initial = make_initial_state(goal="G")
        trajectory, _ = sim.rollout_stateful(initial, ["a", "b", "c", "d", "e", "f"], max_steps=3)
        self.assertEqual(len(trajectory), 3)

    def test_transition_downgrades_confidence_on_ontology_failure(self) -> None:
        from unittest.mock import MagicMock

        engine = MagicMock()
        engine.complete.return_value = '''{"next_state": {"entities": {}, "facts": [], "summary": "The item was removed and is gone"}, "confidence": "high", "key_change": "Removed"}'''
        sim = WorldSimulator(engine=engine)
        state = make_initial_state(goal="Keep item")
        next_state, conf = sim.transition(state, "read the item")
        self.assertEqual(conf, "low")
        self.assertIn("ontology", next_state.get("summary", ""))

    def test_rollout_overall_low_when_one_step_low(self) -> None:
        from unittest.mock import MagicMock

        engine = MagicMock()
        engine.complete.side_effect = [
            '''{"next_state": {"entities": {}, "facts": [], "summary": "Step one done"}, "confidence": "high", "key_change": "Ok"}''',
            '''{"next_state": {"entities": {}, "facts": [], "summary": "The resource was removed and is gone"}, "confidence": "high", "key_change": "Gone"}''',
        ]
        sim = WorldSimulator(engine=engine)
        initial = make_initial_state(goal="G")
        trajectory, overall = sim.rollout_stateful(initial, ["action1", "action2"], max_steps=5)
        self.assertEqual(len(trajectory), 2)
        self.assertEqual(overall, "low")


class TestWorldModelPluggableBackend(unittest.TestCase):
    def test_classical_backend_transition(self) -> None:
        from rain.world.simulator import _classical_transition, make_initial_state

        state = make_initial_state(goal="Test goal")
        next_state, conf = _classical_transition(state, "Do action", context="")
        self.assertIn("summary", next_state)
        self.assertEqual(conf, "high")
        self.assertIn("Do action", next_state["summary"])

    def test_simulator_external_backend(self) -> None:
        from rain.world.simulator import WorldSimulator, make_initial_state

        def custom_transition(state: dict, action: str, context: str):
            return {**state, "summary": f"Custom: {action}"}, "medium"
        sim = WorldSimulator(engine=None)
        sim.set_external_backend(custom_transition)
        state = make_initial_state(goal="G")
        next_state, conf = sim.transition(state, "my action", context="")
        self.assertEqual(conf, "medium")
        self.assertIn("Custom: my action", next_state.get("summary", ""))


class TestPlannerWorldModelIntegration(unittest.TestCase):
    def test_score_plan_with_world_model_returns_confidence_and_trajectory(self) -> None:
        from unittest.mock import MagicMock

        from rain.planning.planner import score_plan_with_world_model

        engine = MagicMock()
        engine.complete.return_value = '''{"next_state": {"entities": {}, "facts": [], "summary": "Ok"}, "confidence": "high", "key_change": "Ok"}'''
        from rain.world.simulator import WorldSimulator

        sim = WorldSimulator(engine=engine)
        steps = [{"id": 1, "action": "step one", "depends": []}, {"id": 2, "action": "step two", "depends": [1]}]
        overall, trajectory = score_plan_with_world_model("Goal", steps, sim, context="", max_rollout_steps=5)
        self.assertIn(overall, ("high", "medium", "low"))
        self.assertIsInstance(trajectory, list)
        self.assertEqual(len(trajectory), 2)
