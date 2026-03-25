# Task type vs recommended Rain path

| Task type | Recommended path | Notes |
|-----------|------------------|--------|
| QA / factual | `python -m rain "question"` or `--chat` | Single turn or chat; use `--memory` for long-term recall. |
| Coding | `--chat --tools` or autonomy with plan | Tools: run_code (if enabled), search, RAG. |
| Planning / multi-step | `python -m rain --autonomy --plan "goal"` | Long-horizon planner; replan on step failure. |
| Creativity / ideation | Moonshot pipeline or `rain.creativity.creative_generate()` | Domains: product_ideas, research_directions, story_premises, strategy_options. |
| Analysis / reasoning | `--chat` with optional COT; set RAIN_DEEP_REASONING_PATHS=2 for hard queries | Deeper reasoning for multi-step or "prove" style. |
| Voice-in | `python -m rain --voice path/to.wav` or `--voice-session` | Transcribe + identify speaker; Vocal Gate for high-risk. |
| Vision | Use describe_image tool (auto-registered when VISION_ENABLED) | Pass image path or base64. |
| Web UI | `python -m rain --web` | Browser at port 8765; optional X-API-Key. |
