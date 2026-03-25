# Improvement Loops (Phase 5.18)

Rain improves within the box: feedback flows into prompts, few-shot examples, and tool docs—with human oversight.

## Feedback sources
- **User corrections**: When the user corrects Rain, the correction is in conversation history; future sessions can use \`recall_similar\` or lessons.
- **Eval results**: Run \`scripts/run_agi_benchmarks.py\` and \`scripts/creativity_eval.py\`; use results to adjust prompts in \`rain/moonshot/prompts.py\`, \`rain/creativity/creative.py\`, or reasoning prompts.
- **Red-team findings**: \`tests/test_value_stability.py\` and \`tests/test_robustness.py\` probe constraints; add new refusal patterns to \`rain/safety/vault.py\` (HARD_FORBIDDEN, SAFETY_OVERRIDE_REQUEST_PATTERNS) when probes find gaps.

## Where to update
- **Prompts**: \`rain/moonshot/prompts.py\`, \`rain/planning/planner.py\` (step prompts), \`rain/reasoning/*.py\`, \`rain/creativity/creative.py\`.
- **Tool docs**: \`rain/tools/*.py\` docstrings and \`list_tools()\` descriptions.
- **Safety**: \`rain/safety/vault.py\` (patterns, refusal message).

## Optional: automated tests on outputs
- Use \`rain.creativity.eval.score_creativity()\` for novelty/usefulness on generated ideas.
- Use \`rain.safety.vault.SafetyVault().check_response(text, prompt)\` in CI on sampled outputs.
- Human oversight: review any new refusal patterns or prompt changes before deploy.
