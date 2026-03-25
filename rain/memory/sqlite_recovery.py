"""Recover from corrupted SQLite files (e.g. sync glitch, truncated file)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path


def init_sqlite_or_rename_corrupt(path: Path, setup: Callable[[sqlite3.Connection], None]) -> None:
    """Open DB and run setup(conn). On DatabaseError, rename path to *.corrupt* once and retry."""
    for attempt in range(2):
        try:
            with sqlite3.connect(path) as conn:
                setup(conn)
            return
        except sqlite3.DatabaseError:
            if attempt == 0 and path.is_file():
                bad = path.with_name(path.name + ".corrupt")
                n = 0
                while bad.exists():
                    n += 1
                    bad = path.with_name(path.name + f".corrupt.{n}")
                path.rename(bad)
                continue
            raise
