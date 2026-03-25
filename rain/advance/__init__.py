"""Rain Advance Stack — opt-in orchestration for stronger, auditable reasoning."""

from rain.advance.stack import (
    extra_system_instructions,
    log_event,
    log_verification_result,
    maybe_peer_review_append,
    routing_context,
)

__all__ = [
    "extra_system_instructions",
    "log_event",
    "log_verification_result",
    "maybe_peer_review_append",
    "routing_context",
]
