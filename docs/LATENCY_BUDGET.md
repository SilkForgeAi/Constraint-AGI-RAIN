# Latency budget (Speed of thinking)

Targets to hit so Rain stays faster than any other AI. Measure with scripts/latency_report.py and/or rain.core.latency.get_percentiles().

- **complete (non-stream)**: p95 time-to-complete < 15s for typical turns (target: < 10s).
- **complete_stream**: p50 time-to-first-token < 500ms; p95 time-to-complete < 12s.

When RAIN_SPEED_PRIORITY=1 we use streaming and skip optional metacog/calibration/verification to reduce round-trips.
