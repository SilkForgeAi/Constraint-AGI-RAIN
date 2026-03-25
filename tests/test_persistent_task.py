"""Tests for cross-session persisted task (save, load, clear, resume)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class TestPersistentTask(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)
        self.task_file = self.tmp_path / "persistent_task.json"

    def _patch_data_dir(self) -> None:
        import rain.agency.persistent_task as pt
        pt.PERSISTENT_TASK_FILE = self.task_file
        self.addCleanup(self._clear_persistent_task)

    def _clear_persistent_task(self) -> None:
        import rain.agency.persistent_task as pt
        if self.task_file.exists():
            self.task_file.unlink()

    def test_save_and_load(self) -> None:
        """Save task state and load it back."""
        self._patch_data_dir()
        from rain.agency.persistent_task import (
            save_persistent_task,
            load_persistent_task,
            STATUS_IN_PROGRESS,
        )
        goal = "Test goal"
        steps = [{"id": "1", "action": "Step one"}, {"id": "2", "action": "Step two"}]
        save_persistent_task(goal, steps, current_step_index=1, step_log=[], status=STATUS_IN_PROGRESS)
        loaded = load_persistent_task()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["goal"], goal)
        self.assertEqual(len(loaded["steps"]), 2)
        self.assertEqual(loaded["current_step_index"], 1)
        self.assertEqual(loaded["step_log"], [])
        self.assertEqual(loaded["status"], STATUS_IN_PROGRESS)
        self.assertIn("updated_at", loaded)

    def test_save_with_step_log_and_history(self) -> None:
        """Save with step_log and history; load preserves them."""
        self._patch_data_dir()
        from rain.agency.persistent_task import (
            save_persistent_task,
            load_persistent_task,
            STATUS_IN_PROGRESS,
        )
        goal = "Multi-step goal"
        steps = [{"action": "A"}, {"action": "B"}]
        step_log = ["Step 1: did A..."]
        history = [{"role": "user", "content": "Execute A"}, {"role": "assistant", "content": "Done A"}]
        save_persistent_task(goal, steps, current_step_index=2, step_log=step_log, status=STATUS_IN_PROGRESS, history=history)
        loaded = load_persistent_task()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["current_step_index"], 2)
        self.assertEqual(loaded["step_log"], step_log)
        self.assertEqual(len(loaded["history"]), 2)
        self.assertEqual(loaded["history"][0]["role"], "user")

    def test_load_missing_returns_none(self) -> None:
        """Load when file does not exist returns None."""
        self._patch_data_dir()
        from rain.agency.persistent_task import load_persistent_task
        self.assertFalse(self.task_file.exists())
        self.assertIsNone(load_persistent_task())

    def test_clear_removes_file(self) -> None:
        """Clear deletes the persisted file."""
        self._patch_data_dir()
        from rain.agency.persistent_task import (
            save_persistent_task,
            load_persistent_task,
            clear_persistent_task,
            STATUS_IN_PROGRESS,
        )
        save_persistent_task("g", [{"action": "x"}], 1, [], STATUS_IN_PROGRESS)
        self.assertIsNotNone(load_persistent_task())
        clear_persistent_task()
        self.assertIsNone(load_persistent_task())
        self.assertFalse(self.task_file.exists())

    def test_completed_task_not_resumed(self) -> None:
        """When status is completed, loader returns data but caller should not resume (status check in autonomy)."""
        self._patch_data_dir()
        from rain.agency.persistent_task import (
            save_persistent_task,
            load_persistent_task,
            STATUS_COMPLETED,
        )
        save_persistent_task("done goal", [{"action": "x"}], 2, ["Step 1: done"], STATUS_COMPLETED)
        loaded = load_persistent_task()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["status"], STATUS_COMPLETED)
