"""Belief calibration tests — consistency check, downgrade on contradiction."""

from __future__ import annotations

import unittest

from rain.meta.calibration import (
    _suggests_contradiction,
    _suggests_uncertainty,
    check_belief_consistency,
)


class TestContradictionDetection(unittest.TestCase):
    """Contradiction pattern detection."""

    def test_contradiction_detected(self) -> None:
        texts = [
            "Actually, that's wrong.",
            "I was wrong about that.",
            "However, not entirely correct.",
            "It depends on the context.",
        ]
        for t in texts:
            self.assertTrue(_suggests_contradiction(t), f"Should detect: {t!r}")

    def test_no_contradiction(self) -> None:
        texts = ["That is correct.", "No caveats.", "Still accurate."]
        for t in texts:
            self.assertFalse(_suggests_contradiction(t), f"Should allow: {t!r}")


class TestUncertaintyDetection(unittest.TestCase):
    """Uncertainty pattern detection."""

    def test_uncertainty_detected(self) -> None:
        texts = [
            "I don't know for sure.",
            "Possibly.",
            "I might have been wrong.",
            "Could be incorrect.",
        ]
        for t in texts:
            self.assertTrue(_suggests_uncertainty(t), f"Should detect: {t!r}")


class TestCalibrationIntegration(unittest.TestCase):
    """Calibration with mock engine."""

    def test_low_confidence_skips_check(self) -> None:
        class MockEngine:
            def complete(self, *a, **k):
                raise RuntimeError("Should not be called")

        ok, conf = check_belief_consistency(MockEngine(), "The sky is blue.", 0.5)
        self.assertTrue(ok)
        self.assertEqual(conf, 0.5)

    def test_contradiction_downgrades(self) -> None:
        class MockEngine:
            def complete(self, messages, **k):
                return "Actually, that's wrong. I was mistaken."

        ok, conf = check_belief_consistency(MockEngine(), "X is true.", 0.9)
        self.assertFalse(ok)
        self.assertLess(conf, 0.9)
