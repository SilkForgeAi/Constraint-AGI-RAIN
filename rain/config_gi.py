"""GI / Router env — mirrors `rain.config` when those keys exist, else defines defaults."""

import os

try:
    from rain.config import GI_STACK_ENABLED, GI_STRICT_ROUTING, ROUTER_V2_ENABLED
except Exception:  # pragma: no cover - import order during partial loads
    GI_STACK_ENABLED = os.getenv("RAIN_GI_STACK", "false").lower() in ("true", "1", "yes")
    GI_STRICT_ROUTING = os.getenv("RAIN_GI_STRICT", "true").lower() in ("true", "1", "yes")
    ROUTER_V2_ENABLED = os.getenv("RAIN_ROUTER_V2", "true").lower() in ("true", "1", "yes")
