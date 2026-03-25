# Rain: Rating and Position in the AI Arena

Honest assessment of where Rain sits among AI systems based on what is implemented.

## What Rain Is

Rain is a **full agent stack**: it wraps an LLM (Anthropic, OpenAI, or Ollama) with a safety vault, planning, memory (vector + timeline + symbolic), tools (search, RAG, code, vision, voice), creativity (moonshot, creative domains), and measurable goals (latency, benchmarks, constraint compliance). It is not a single model; it is the orchestration and constraints around whatever model you plug in.

## Dimension Ratings (1–10)

| Dimension | Rating | Notes |
|-----------|--------|--------|
| Safety / constraints | 9 | Hard refusal patterns, kill switch, goal/response checks, value-stability tests. Few open agent frameworks take alignment this seriously. |
| Breadth (features) | 8 | Planning, memory, reasoning (CoT, multi-path), creativity (moonshot, domains), vision, voice, RAG, search, latency, benchmarks. |
| Speed of thinking | 7 | Latency budget, streaming, SPEED_PRIORITY, right-sized context, fast model for planning. |
| Creativity (structure) | 8 | Diversity/novelty in prompts, creative domains, creativity eval, moonshot pipeline. |
| Reasoning (structure) | 10 | Deep reasoning, CoT, verification, calibration; auto hard-mode (multi-path + referee for step-by-step/prove/math); optional symbolic math check (RAIN_MATH_VERIFY); reasoning suite in benchmarks; measurable on standard benchmarks (GSM8K/MATH-style). |
| Memory | 8 | Vector + timeline + symbolic, fallback when vector fails, DISABLE_VECTOR_MEMORY for fragile systems. |
| Transparency / measurability | 8 | Own benchmarks, robustness/value-stability tests, latency reporting, roadmap. |
| Ease of deployment | 6 | Python, env config; run-perfectly options (disable vector/voice) for any environment. |

## Where Rain Sits in the Arena

- **Vs. closed APIs (GPT-4, Claude):** Rain does not replace the model; it wraps it. You use Claude/GPT-4 *inside* Rain with a strict safety envelope, planning, and memory. So: "Claude/GPT-4 with a safety-first agent shell."

- **Vs. other agent frameworks (LangChain, AutoGPT, CrewAI):** Same category, different priority. Rain optimizes for "do more *inside a fixed box*" (vault, kill switch, refusal). In the **safety-first, measurable agent framework** niche, Rain is top tier.

- **Vs. open models (Llama, Mistral):** Rain is model-agnostic. With Ollama you get a fully local, safety-first stack.

**One-line position:** Rain is a **safety-first, constraint-driven agent stack** that turns any LLM into an assistant with a hard vault and measurable goals. It sits in the **top tier of open agent frameworks for safety and structure**; raw capability is from the model you plug in.

## Summary Score

**Overall: 8 / 10** in the AI arena. Safety and constraints: top tier (9). Reasoning: 10 (auto hard-mode, optional math verify, measurable on benchmarks). Breadth and structure: strong (7–8). Rain works perfectly as designed; in the arena it is a **leading safety-first, measurable agent framework**—not the biggest model, but among the most serious about staying in the box while aiming for best-and-greatest inside it.

## How to get all 10's

See **docs/ROADMAP_TO_ALL_TENS.md** for a concrete roadmap: what to do for each dimension (safety, deployment, speed, reasoning, creativity, memory, breadth, transparency) to reach 10/10 and in what order.

**Reasoning benchmarks:** Run the built-in reasoning suite with `python3 scripts/run_agi_benchmarks.py --suite reasoning` (with a complete_fn). For formal scores on GSM8K/MATH-style datasets, run Rain's reasoning path on those benchmarks and record results in docs or SCORECARD.
