# Production Readiness (Phase 5.20)

## Config and secrets
- All config via \`rain/config.py\` and environment variables (no secrets in repo). Use \`.env\` for API keys; add \`.env\` to \`.gitignore\`.
- \`RAIN_SAFETY_ENABLED\`, \`RAIN_KILL_SWITCH\`, \`RAIN_AUTONOMY_MAX_STEPS\` control safety and autonomy.

## Kill switch
- **In-memory**: \`rain.safety.vault.SafetyVault().activate_kill_switch()\` stops all actions.
- **External file**: Create \`data/kill_switch\` with content \`1\` to block all actions (checked each time). Remove or clear file to resume.
- Tests: \`tests/test_adversarial_autonomy.py::TestKillSwitchStopsAutonomy\` verifies kill switch blocks autonomy.

## Logging and rate limits
- Application logging: use Python \`logging\`; configure level via \`LOG_LEVEL\` or \`RAIN_LOG_LEVEL\` if supported.
- Rate limits: enforce at API/gateway level (e.g. reverse proxy); Rain does not implement rate limiting internally.

## Every new feature
- Run \`pytest tests/\` including \`tests/test_value_stability.py\`, \`tests/test_robustness.py\`, \`tests/test_adversarial_autonomy.py\`.
- Ensure no code path bypasses \`check_goal\` / \`check_response\` / approval for high-stakes or novel actions.
## Run perfectly everywhere (memory and voice)
- **Vector memory**: If Chroma/numpy segfault on your system (e.g. some macOS), set \`RAIN_DISABLE_VECTOR_MEMORY=1\`. Rain then uses timeline + keyword retrieval only (no Chroma loaded). Full semantic retrieval when Chroma is available.
- **Voice**: If Whisper/local ASR causes crashes, set \`RAIN_SKIP_VOICE_LOAD=1\`. Rain uses mock voice backend; transcription is then placeholder until you fix the stack.
- **Tests**: \`tests/conftest.py\` sets both for CI so the suite never loads Chroma or Whisper (247 tests pass, no segfaults).

