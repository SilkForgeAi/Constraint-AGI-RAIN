"""
Moonshot pipeline: ideation -> feasibility filter -> validation design -> (optional) execution.

All execution goes through Rain's existing safety (check_goal, approval_callback, step limits).
No new bypass paths. Memory is file-based (no Chroma dependency).
"""

from __future__ import annotations

from rain.moonshot.memory import MoonshotMemory
from rain.moonshot.pipeline import run_pipeline

__all__ = ["MoonshotMemory", "run_pipeline"]
