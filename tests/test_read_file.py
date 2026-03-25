"""Tests for read_file tool — allowlist, read-only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class TestReadFile(unittest.TestCase):
    def test_read_file_disabled_returns_message(self) -> None:
        import rain.config as cfg
        from rain.tools.read_file import read_file

        orig = cfg.READ_FILE_ENABLED
        try:
            cfg.READ_FILE_ENABLED = False
            r = read_file("docs/README.md")
            self.assertIn("disabled", r.lower())
        finally:
            cfg.READ_FILE_ENABLED = orig

    def test_read_file_rejects_parent_traversal(self) -> None:
        import rain.config as cfg
        from rain.tools.read_file import read_file

        orig = cfg.READ_FILE_ENABLED
        try:
            cfg.READ_FILE_ENABLED = True
            r = read_file("../../../etc/passwd")
            self.assertIn("Error", r)
        finally:
            cfg.READ_FILE_ENABLED = orig

    def test_read_file_reads_under_project(self) -> None:
        import rain.config as cfg
        from rain.tools.read_file import read_file

        orig = cfg.READ_FILE_ENABLED
        try:
            cfg.READ_FILE_ENABLED = True
            # Read a file that exists under project
            r = read_file("rain/config.py")
            self.assertIn("RAIN_ROOT", r)
        finally:
            cfg.READ_FILE_ENABLED = orig
