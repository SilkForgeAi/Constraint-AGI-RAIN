"""
Creativity as a product: creative domains (product ideas, research directions, story premises, strategy options)
with diversity and novelty as explicit objectives. No safety bypasses; uses Rain's engine and safety.
"""

from __future__ import annotations

from rain.creativity.creative import creative_generate
from rain.creativity.eval import score_creativity
from rain.creativity.transfer import record_domain_lesson, get_lessons_for_domain, inject_transfer_context

__all__ = ["creative_generate", "score_creativity", "record_domain_lesson", "get_lessons_for_domain", "inject_transfer_context"]
