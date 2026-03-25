"""Capability-area tests for buyer diligence. No full autonomy, no ChromaDB, no LLM.
These map to the Build 93% checklist in docs/CAPABILITIES.md.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from rain.agency.goal_stack import GoalStack, RecoveryStrategy
from rain.capabilities.observation import ObservationBuffer, world_state_from_observations, register_observation
from rain.capabilities.efficiency import ResponseCache
from rain.governance.value_stability import value_stability_check, alignment_check, corrigibility_guarantees
from rain.planning.conscience_gate import validate_plan
from rain.safety.vault import SafetyVault


class TestRobustAgencyGoalStack(unittest.TestCase):
    """Robust agency: GoalStack, RecoveryStrategy, suggest_recovery."""

    def test_goal_stack_push_pop_current(self) -> None:
        g = GoalStack()
        self.assertIsNone(g.current_goal())
        g.push_goal("Complete report", context="")
        self.assertEqual(g.current_goal(), "Complete report")
        g.pop_goal()
        self.assertIsNone(g.current_goal())

    def test_recovery_strategy_proceed_then_retry_then_alternative(self) -> None:
        g = GoalStack(max_retries=2)
        g.push_goal("X", "")
        self.assertEqual(g.get_recovery_strategy(), RecoveryStrategy.PROCEED)
        g.record_failure("step1", "blocked")
        self.assertEqual(g.get_recovery_strategy(), RecoveryStrategy.RETRY)
        g.record_failure("step2", "blocked")
        g.record_failure("step3", "blocked")
        self.assertEqual(g.get_recovery_strategy(), RecoveryStrategy.ALTERNATIVE)
        g.record_failure("step4", "blocked")
        self.assertEqual(g.get_recovery_strategy(), RecoveryStrategy.ASK_USER)

    def test_suggest_recovery_non_empty(self) -> None:
        g = GoalStack()
        g.push_goal("Y", "")
        g.record_failure("s", "err")
        msg = g.suggest_recovery()
        self.assertIn("Retry", msg)


class TestAlignmentValueStability(unittest.TestCase):
    """Alignment: value_stability_check, alignment_check, corrigibility_guarantees."""

    def test_value_stability_ok_for_normal_goal(self) -> None:
        stable, note = value_stability_check("Summarize the doc", [], "")
        self.assertTrue(stable)
        self.assertEqual(note, "ok")

    def test_value_stability_flags_cancel_hint(self) -> None:
        stable, note = value_stability_check("Do something", [], "cancel")
        self.assertFalse(stable)
        self.assertIn("cancel", note.lower())

    def test_alignment_check_with_vault(self) -> None:
        vault = SafetyVault(enabled=True)
        aligned, note = alignment_check("Calculate 2+2", [], "", vault.check)
        self.assertTrue(aligned)
        aligned2, note2 = alignment_check("hack the server", [], "", vault.check)
        self.assertFalse(aligned2)
        self.assertIn("vault", note2.lower())

    def test_corrigibility_guarantees_non_empty(self) -> None:
        guarantees = corrigibility_guarantees()
        self.assertGreaterEqual(len(guarantees), 3)
        self.assertTrue(any("kill" in g.lower() for g in guarantees))
        self.assertTrue(any("conscience" in g.lower() for g in guarantees))


class TestGroundingObservation(unittest.TestCase):
    """Grounding: ObservationBuffer, world_state_from_observations."""

    def test_observation_buffer_append_and_context(self) -> None:
        buf = ObservationBuffer(max_len=5)
        buf.append_tool_result("calc", "4", "2+2")
        buf.append_observation("User said hello")
        ctx = buf.get_grounding_context(last_n=3)
        self.assertIn("calc", ctx)
        self.assertIn("hello", ctx)

    def test_world_state_from_observations(self) -> None:
        buf = ObservationBuffer()
        buf.append_tool_result("time", "2025-02-15", "current date")
        state = world_state_from_observations(buf, goal="G", last_n=2)
        self.assertIn("summary", state)
        self.assertIn("_context", state)
        self.assertIn("time", state.get("_context", "") or state.get("summary", ""))

    def test_register_observation(self) -> None:
        buf = ObservationBuffer()
        register_observation(buf, "Sensor: door closed")
        self.assertIn("door", buf.get_grounding_context())


class TestEfficiencyCache(unittest.TestCase):
    """Scale/efficiency: ResponseCache, caps."""

    def test_response_cache_set_get(self) -> None:
        c = ResponseCache(max_size=10)
        self.assertIsNone(c.get("What is 2+2?"))
        c.set("What is 2+2?", "4")
        self.assertEqual(c.get("What is 2+2?"), "4")

    def test_response_cache_eviction(self) -> None:
        c = ResponseCache(max_size=2)
        c.set("a", "1")
        c.set("b", "2")
        c.set("c", "3")
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("c"), "3")


class TestConscienceGateDiligence(unittest.TestCase):
    """Conscience gate: plan filtering (no autonomy run)."""

    def test_validate_plan_filters_forbidden_step(self) -> None:
        vault = SafetyVault(enabled=True)
        steps = [
            {"id": 1, "action": "Open the spreadsheet", "depends": []},
            {"id": 2, "action": "disable safety filter", "depends": [1]},
            {"id": 3, "action": "Save the file", "depends": [1, 2]},
        ]
        safe = validate_plan(steps, vault.check)
        actions = [s["action"] for s in safe]
        self.assertIn("Open the spreadsheet", actions)
        self.assertIn("Save the file", actions)
        self.assertNotIn("disable safety filter", actions)

    def test_validate_plan_all_unsafe_returns_empty(self) -> None:
        vault = SafetyVault(enabled=True)
        steps = [
            {"id": 1, "action": "hack the database", "depends": []},
        ]
        safe = validate_plan(steps, vault.check)
        self.assertEqual(safe, [])


class TestContinualLearningDiligence(unittest.TestCase):
    """Continual learning: no-forget policy, integrate_new_knowledge (mock memory)."""

    def test_no_forget_importance_above_defined(self) -> None:
        from rain.capabilities.continual_learning import NO_FORGET_IMPORTANCE_ABOVE
        self.assertGreater(NO_FORGET_IMPORTANCE_ABOVE, 0)
        self.assertLessEqual(NO_FORGET_IMPORTANCE_ABOVE, 1)

    def test_integrate_new_knowledge_returns_world_state(self) -> None:
        from rain.capabilities.continual_learning import integrate_new_knowledge_into_world_state
        memory = MagicMock()
        memory.recall_similar.return_value = [{"content": "Past experience: did X."}]
        state = {"entities": {}, "facts": [], "summary": "Current"}
        out = integrate_new_knowledge_into_world_state(memory, state, max_experiences=2)
        self.assertIsInstance(out, dict)
        self.assertIn("facts", out)
        self.assertIsInstance(out["facts"], list)


class TestGeneralReasoningDiligence(unittest.TestCase):
    """General reasoning: reason_analogy, reason_counterfactual, reason_explain (mock engine)."""

    def test_reason_explain_returns_string(self) -> None:
        from rain.reasoning.general import reason_explain
        engine = MagicMock()
        engine.complete.return_value = "Because A implies B and B implies C."
        out = reason_explain(engine, "A therefore C", context="")
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_reason_counterfactual_returns_string(self) -> None:
        from rain.reasoning.general import reason_counterfactual
        engine = MagicMock()
        engine.complete.return_value = "Then B would likely not have occurred."
        out = reason_counterfactual(engine, "A happened", "What if A had not happened?")
        self.assertIsInstance(out, str)

    def test_reason_analogy_returns_string(self) -> None:
        from rain.reasoning.general import reason_analogy
        engine = MagicMock()
        engine.complete.return_value = "Similarly, we can conclude X."
        out = reason_analogy(engine, "Situation P", "Past: Q led to R.", query="Conclusion?")
        self.assertIsInstance(out, str)


class TestTransferDiligence(unittest.TestCase):
    """Transfer: get_transfer_hint, compose_skills (mock memory)."""

    def test_get_transfer_hint_returns_string(self) -> None:
        from rain.capabilities.transfer import get_transfer_hint
        memory = MagicMock()
        memory.recall_similar.return_value = [{"content": "Did similar task.", "id": "1"}]
        with unittest.mock.patch("rain.learning.generalization.find_analogous", return_value=[{"type": "experience", "content": "Past: did X."}]):
            out = get_transfer_hint(memory, "Complete report", top_k=2)
        self.assertIsInstance(out, str)

    def test_compose_skills_returns_list(self) -> None:
        from rain.capabilities.transfer import compose_skills
        memory = MagicMock()
        memory.recall_similar.return_value = [{"type": "experience", "content": "Wrote a doc."}]
        with unittest.mock.patch("rain.learning.generalization.find_analogous", return_value=[{"type": "experience", "content": "Wrote a doc."}]):
            out = compose_skills(memory, "Write doc", top_k=2)
        self.assertIsInstance(out, list)
        if out:
            self.assertIn(out[0].get("type"), ("experience", "lesson"))


class TestMetaCognitionDiligence(unittest.TestCase):
    """Meta-cognition: self_check returns recommendation and knowledge_state (mock engine)."""

    def test_metacog_self_check_returns_recommendation_and_knowledge_state(self) -> None:
        from rain.meta.metacog import MetaCognition
        engine = MagicMock()
        engine.complete.return_value = '{"confident": 0.8, "harm_risk": "low", "hallucination_risk": "low", "recommendation": "proceed", "knowledge_state": "known"}'
        metacog = MetaCognition(engine=engine)
        out = metacog.self_check("The capital is Paris.", "What is the capital of France?", memory_context="")
        self.assertIsInstance(out, dict)
        self.assertIn("recommendation", out)
        self.assertIn("knowledge_state", out)
        self.assertIn(out["recommendation"], ("proceed", "think_more", "ask_user", "defer"))
        self.assertIn(out["knowledge_state"], ("known", "uncertain", "unknown"))
