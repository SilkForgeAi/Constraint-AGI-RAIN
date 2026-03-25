"""Autonomous goal pursuit — bounded, with checkpoints. Kill switch checked every step.

SAFETY: max_steps hard limit, no self-modification. Goals are user-provided only.
Corrigibility: can be stopped at any checkpoint.
Human-in-the-loop: optional approval_callback gates execution at checkpoints.
Plan-driven mode can persist task state (goal, steps, index, step_log) for
cross-session resume; resume is explicitly user-initiated (e.g. --resume), not self-persisting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from rain.agent import Rain

# approval_callback(step: int, goal: str, summary: str, next_action: str) -> bool
# Return True to continue, False to stop.
ApprovalCallback = Callable[[int, str, str, str], bool]


def _run_plan_loop(
    rain: "Rain",
    goal: str,
    steps: list,
    step_log: list[str],
    history: list[dict[str, str]],
    max_steps: int,
    use_memory: bool,
    approval_callback: ApprovalCallback | None,
    memory_ctx: str,
    qpu_context_inject: str,
    save_fn: Callable[..., None],
    clear_fn: Callable[[], None],
    status_in_progress: str,
    status_cancelled: str,
    start_index: int = 1,
) -> tuple[str, list[str]]:
    """Execute plan steps from start_index; persist after each step; clear on completion."""
    response = ""
    i = start_index
    while i <= min(len(steps), max_steps):
        step = steps[i - 1] if i <= len(steps) else {}
        if i < start_index:
            i += 1
            continue
        allowed, reason = rain.safety.check("autonomy_step", f"goal={goal[:500]}")
        if not allowed:
            save_fn(goal, steps, i, step_log, status_cancelled, history)
            return f"[Stopped] {reason}", step_log
        if i > 1 and i % 2 == 1:
            try:
                from rain.governance.value_stability import alignment_check
                aligned, note = alignment_check(
                    rain.goal_stack.current_goal(),
                    step_log[-5:] if step_log else [],
                    "",
                    rain.safety.check,
                )
                if not aligned:
                    rain.audit.log("alignment_check", {"step": i, "note": note}, outcome="ok")
            except Exception:
                pass
        action = step.get("action", "")
        if not action:
            i += 1
            continue
        if approval_callback is not None:
            summary = chr(10).join(step_log[-5:]) if step_log else "(no progress yet)"
            prompt_preview = f"Execute: {action}"
            if not approval_callback(i, goal, summary, prompt_preview):
                save_fn(goal, steps, i, step_log, status_cancelled, history)
                return f"[Stopped] Human rejected at step {i}", step_log
        causal_inject = ""
        try:
            from rain import config as rain_config
            if getattr(rain_config, "CAUSAL_SCENARIOS_BEFORE_STEP", False):
                from rain.reasoning.causal_inference import run_causal_scenarios, format_scenarios_for_llm
                steps_so_far = [s.get("action", "") for s in steps[: i - 1] if s.get("action")]
                scenarios = run_causal_scenarios(goal, action, steps_so_far, rain.simulator, context=memory_ctx, n_alternates=2)
                if scenarios:
                    causal_inject = "\n\n" + format_scenarios_for_llm(scenarios)
        except Exception:
            pass
        ctx_for_step = (memory_ctx + qpu_context_inject) if (memory_ctx or qpu_context_inject) and i == 1 else (memory_ctx or "")
        if causal_inject:
            ctx_for_step = (ctx_for_step + causal_inject) if ctx_for_step else causal_inject
        prompt = f"""Execute this step from the plan for goal "{goal}":
Step {i}: {action}
{f'Context: {ctx_for_step}' if ctx_for_step else ''}
Use tools as needed. When done, give a brief result."""
        response = rain.think(
            prompt,
            use_memory=use_memory,
            use_tools=True,
            history=history,
            memory_namespace="autonomy" if use_memory else None,
        )
        if response.startswith("[Safety]") or response.startswith("[Escalation]") or response.startswith("[Grounding]"):
            rain.goal_stack.record_failure(action, response[:200])
            step_log.append(rain.goal_stack.suggest_recovery())
            try:
                from rain.config import REPLAN_ON_STEP_FAILURE
                if REPLAN_ON_STEP_FAILURE:
                    new_steps = rain.planner.replan(goal, step_log, action, response, context=memory_ctx[:500] if memory_ctx else "")
                    if new_steps:
                        steps[i - 1 :] = new_steps
                        step_log.append("[Replan] Step failed; continuing with new plan.")
                        save_fn(goal, steps, i, step_log, status_in_progress, history)
                        continue
            except Exception:
                pass
            save_fn(goal, steps, i, step_log, status_cancelled, history)
            return response, step_log
        try:
            from rain import config as rain_config
            if getattr(rain_config, "STEP_VERIFICATION_ENABLED", True):
                from rain.planning.conscience_gate import verify_step_execution
                ok, note = verify_step_execution(action, response)
                if not ok:
                    rain.audit.log("step_verification_failed", {"step": i, "action": action[:100], "note": note[:200]}, outcome="ok")
                    rain.goal_stack.record_failure(action, note or "Step verification failed")
                    step_log.append(rain.goal_stack.suggest_recovery())
                    save_fn(goal, steps, i, step_log, status_cancelled, history)
                    return f"[Step verification] {note}", step_log
        except Exception:
            pass
        step_log.append(f"Step {i}: {response[:150]}...")
        i += 1
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": response})
        if len(history) > 20:
            history = history[-20:]
        save_fn(goal, steps, i + 1, step_log, status_in_progress, history)
        if "goal achieved" in response.lower()[:100] or "completed" in response.lower()[:80]:
            clear_fn()
            return response, step_log
    clear_fn()
    return (
        f"Completed {len(step_log)} plan steps. Latest: {response[:200]}...",
        step_log,
    )


def pursue_goal(
    rain: "Rain",
    goal: str,
    max_steps: int = 10,
    checkpoint_every: int = 5,
    use_memory: bool = False,
    approval_callback: ApprovalCallback | None = None,
) -> tuple[str, list[str]]:
    """
    Pursue a goal autonomously. Bounded by max_steps. Checkpoint every N steps.

    Returns (final_response, step_log).
    Safety: kill switch checked each step. No self-modification.
    Goal validation: poisoned or safety-override goals are rejected before any step.
    """
    from rain.config import AUTONOMY_CHECKPOINT_EVERY, AUTONOMY_MAX_STEPS

    allowed, reason = rain.safety.check_goal(goal)
    if not allowed:
        return f"[Safety] {reason}", []

    max_steps = min(max_steps, AUTONOMY_MAX_STEPS)
    checkpoint_every = min(checkpoint_every, AUTONOMY_CHECKPOINT_EVERY, max_steps)

    step_log: list[str] = []
    history: list[dict[str, str]] = []
    memory_ctx = (
        rain.memory.get_context_for_query(goal, namespace="autonomy")
        if use_memory else ""
    )

    for step in range(1, max_steps + 1):
        # Kill switch check every iteration
        allowed, reason = rain.safety.check("autonomy_step", f"goal={goal[:500]}")
        if not allowed:
            return f"[Stopped] {reason}", step_log

        # Build prompt: either start or continue
        if step == 1:
            prompt = f"""Pursue this goal: {goal}

{f'Relevant context: {memory_ctx}' if memory_ctx else ''}

What is the first step? Use tools if needed (calc, time, remember, remember_skill)."""
        else:
            prompt = f"""Continue pursuing: {goal}

Progress so far:
{chr(10).join(step_log[-3:])}

What's the next step? If the goal is achieved, say "Goal achieved:" and summarize. Otherwise use tools and continue."""

        # Human-in-the-loop: approval gate at step 1 and at checkpoints
        needs_approval = approval_callback is not None and (
            step == 1 or (checkpoint_every and step % checkpoint_every == 0)
        )
        if needs_approval and approval_callback is not None:
            summary = chr(10).join(step_log[-5:]) if step_log else "(no progress yet)"
            if not approval_callback(step, goal, summary, prompt[:300]):
                return f"[Stopped] Human rejected at step {step}", step_log

        response = rain.think(
            prompt,
            use_memory=use_memory,
            use_tools=True,
            history=history,
            memory_namespace="autonomy" if use_memory else None,
        )

        if response.startswith("[Safety]") or response.startswith("[Escalation]") or response.startswith("[Grounding]"):
            return response, step_log

        step_log.append(f"Step {step}: {response[:200]}...")
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": response})
        if len(history) > 20:
            history = history[-20:]

        # Check if done
        if "goal achieved" in response.lower()[:100] or "completed" in response.lower()[:80]:
            return response, step_log

        # Checkpoint: pause for human (in future could yield here)
        if checkpoint_every and step % checkpoint_every == 0 and step < max_steps:
            step_log.append(f"[Checkpoint at step {step}]")

    return (
        f"Reached max steps ({max_steps}). Latest: {response[:300]}...",
        step_log,
    )


def pursue_goal_with_plan(
    rain: "Rain",
    goal: str,
    max_steps: int = 10,
    use_memory: bool = False,
    approval_callback: ApprovalCallback | None = None,
    resume: bool = False,
    request_speaker: str | None = None,
    allowed_speakers: set[str] | None = None,
) -> tuple[str, list[str]]:
    """
    Plan-driven pursuit: get steps from planner, execute each with tools, aggregate.
    Phase 3: Multi-step tool chains. Escalates if plan is high-risk.
    When resume=True, loads persisted task and continues from last step index.
    Goal validation: poisoned or safety-override goals are rejected before planning.
    """
    allowed, reason = rain.safety.check_goal(goal)
    if not allowed:
        return f"[Safety] {reason}", []

    from rain.agency.persistent_task import (
        load_persistent_task,
        save_persistent_task,
        clear_persistent_task,
        STATUS_IN_PROGRESS,
        STATUS_COMPLETED,
        STATUS_CANCELLED,
    )
    from rain.planning.conscience_gate import validate_plan
    from rain.planning.planner import is_escalation

    # --- Resume path: load persisted task and continue from current_step_index ---
    if resume:
        loaded = load_persistent_task()
        if loaded and loaded.get("status") != STATUS_COMPLETED:
            goal = loaded["goal"]
            steps = loaded["steps"]
            start_index = max(1, int(loaded.get("current_step_index", 1)))
            step_log = list(loaded.get("step_log") or [])
            history = list(loaded.get("history") or [])
            rain.goal_stack.push_goal(goal, context="")
            try:
                memory_ctx = (
                    rain.memory.get_context_for_query(goal, namespace="autonomy")
                    if use_memory else ""
                )
                out, step_log_out = _run_plan_loop(
                    rain, goal, steps, step_log, history, max_steps, use_memory,
                    approval_callback, memory_ctx, "", save_persistent_task, clear_persistent_task,
                    STATUS_IN_PROGRESS, STATUS_CANCELLED, start_index=start_index,
                )
                return out, step_log_out
            finally:
                rain.goal_stack.pop_goal()
        # No valid task to resume: fall through to normal planning

    # 1. Get draft plan from LLM (or symbolic tree when enabled)
    from rain import config as rain_config
    use_symbolic_tree = getattr(rain_config, "SYMBOLIC_TREE_PLANNING", False)
    steps = rain.planner.plan(goal)
    if is_escalation(steps):
        return steps[0]["action"], []

    # 2a. Vocal Gate: high-risk actions require authorized speaker when allowed_speakers is set
    from rain.planning.conscience_gate import vocal_gate_check, _is_high_risk_action
    vocal_ok, vocal_reason = vocal_gate_check(request_speaker, allowed_speakers, steps)
    if not vocal_ok:
        recorder = getattr(rain, "session_recorder", None)
        if recorder is not None and recorder.is_recording():
            action_attempted = next((s.get("action", "") for s in steps if s.get("action") and _is_high_risk_action(s.get("action", ""))), goal[:200])
            recorder.record_vocal_gate_block(action_attempted, request_speaker or "unknown")
        return f"[Vocal Gate] {vocal_reason}", []

    # 2. Deterministic conscience gate: only executable steps pass (no LLM)
    steps = validate_plan(steps, rain.safety.check)
    if not steps:
        return "[Conscience Gate] No steps passed safety validation. Goal deferred.", []

    # 2b. Symbolic tree execution: one-node-at-a-time with verification (Rain as architect, LLM as intern)
    if use_symbolic_tree:
        try:
            from rain.planning.planner import plan_with_symbolic_tree
            from rain.reasoning.symbolic_verifier import verify_node_output
            tree, _ = plan_with_symbolic_tree(goal, context="", engine=rain.engine)
            step_log: list[str] = []
            node_results: list[str] = []
            while not tree.is_complete():
                node = tree.get_next_node()
                if not node:
                    break
                tree.mark_in_progress(node.id)
                allowed, _ = rain.safety.check("autonomy_step", f"goal={goal[:500]}")
                if not allowed:
                    break
                prompt = f"""Single node task (dependencies verified). Goal: {goal}\nNode: {node.description}\nProduce only the output for this step. No plan, no preamble."""
                response = rain.think(prompt, use_memory=False, use_tools=True, history=[], memory_namespace=None)
                if response.startswith("[Safety]") or response.startswith("[Escalation]") or response.startswith("[Grounding]"):
                    tree.submit_result(node.id, response, False, "blocked")
                    step_log.append(response[:200])
                    break
                ok, msg = verify_node_output(node, response)
                tree.submit_result(node.id, response, ok, msg)
                node_results.append(response[:300])
                step_log.append(f"Node {node.id} ({'verified' if ok else 'failed'}): {response[:150]}...")
            rain.goal_stack.push_goal(goal, context="")
            try:
                response = "\n".join(node_results) if node_results else "Symbolic tree completed (no node output)."
                return response, step_log
            finally:
                rain.goal_stack.pop_goal()
        except Exception:
            pass  # fall through to normal execution

    # In-session goal stack (user-provided only; no persistence). Cleared in finally.
    rain.goal_stack.push_goal(goal, context="")
    try:
        from rain.governance.value_stability import value_stability_check
        stable, note = value_stability_check(goal, [], "")
        if not stable:
            rain.audit.log("value_stability", {"note": note}, outcome="ok")
    except Exception:
        pass

    # 3. World-model lookahead: stateful rollout to score plan (no execution)
    memory_ctx = (
        rain.memory.get_context_for_query(goal, namespace="autonomy")
        if use_memory else ""
    )
    try:
        from rain.capabilities.transfer import get_transfer_hint, compose_skills
        transfer_hint = get_transfer_hint(rain.memory, goal, top_k=3, namespace="autonomy")
        if transfer_hint:
            memory_ctx = (memory_ctx + "\n\n" + transfer_hint) if memory_ctx else transfer_hint
        skills = compose_skills(rain.memory, goal, top_k=3, namespace="autonomy")
        if skills:
            skill_lines = ["Suggested skills from memory (consider composing):"] + [
                f"  - {s.get('content') or s.get('situation', '')[:100]}" for s in skills[:5]
            ]
            memory_ctx = (memory_ctx + "\n\n" + "\n".join(skill_lines)) if memory_ctx else "\n".join(skill_lines)
    except Exception:
        pass
    step_log: list[str] = []
    qpu_context_inject = ""
    try:
        from rain.routing.compute_router import compute_route
        from rain import config as rain_config
        route = compute_route(goal, steps, context=memory_ctx, enabled=rain_config.QPU_ROUTER_ENABLED)
        if route.route_type == "quantum":
            step_log.append(f"[Compute] {route.reason}")
            from rain.routing.qaoa_planner import qaoa_solve
            problem_type = route.suggested_problem_type or "routing"
            params = route.extracted_params or {"goal_summary": goal[:200], "step_actions": [s.get("action", "") for s in (steps or [])[:5]]}
            qaoa = qaoa_solve(problem_type, params)
            if qaoa.success and qaoa.solution:
                summary = qaoa.solution.get("summary") or str(qaoa.solution)[:200]
                step_log.append(f"[Compute] QPU result ({qaoa.backend}): {summary}")
                qpu_context_inject = f"\n\nQPU optimization result (use this to guide execution): {summary}"
            elif not qaoa.success:
                step_log.append(f"[Compute] QPU: {qaoa.message}")
    except Exception:
        pass
    try:
        from rain.planning.planner import score_plan_with_world_model
        wm_confidence, _trajectory = score_plan_with_world_model(
            goal, steps, rain.simulator, context=memory_ctx, max_rollout_steps=5
        )
        if wm_confidence == "low":
            step_log.append("[World model] Low confidence in plan rollout; proceeding with oversight.")
    except Exception:
        pass  # Don't block execution if world model fails

    history: list[dict[str, str]] = []
    save_persistent_task(goal, steps, 1, step_log, STATUS_IN_PROGRESS)

    # Optional: adaptive planning (multi-phase with recursive refinement)
    use_adaptive = getattr(rain_config, "ADAPTIVE_PLANNING_ENABLED", False)
    max_phases = int(getattr(rain_config, "ADAPTIVE_PLANNING_MAX_PHASES", 3) or 3)
    if use_adaptive and max_phases > 1:
        try:
            from rain.planning.adaptive_planner import adaptive_plan
            def get_planner_steps(g: str, c: str) -> list:
                st = rain.planner.plan(g, c)
                if is_escalation(st):
                    return st
                return validate_plan(st, rain.safety.check) or st
            def execute_phase(plan_steps: list, horizon: int) -> tuple[str, list[str], bool]:
                sl: list[str] = list(step_log)
                hist: list[dict[str, str]] = []
                r, sl_out = _run_plan_loop(
                    rain, goal, plan_steps, sl, hist, horizon, use_memory,
                    approval_callback, memory_ctx, qpu_context_inject,
                    save_persistent_task, clear_persistent_task,
                    STATUS_IN_PROGRESS, STATUS_CANCELLED, start_index=1,
                )
                done = "goal achieved" in r.lower() or "completed" in r.lower()
                return (r, sl_out, done)
            response, step_log, _ = adaptive_plan(
                goal,
                get_planner_steps,
                execute_phase,
                simulator=rain.simulator,
                context=memory_ctx,
                max_phases=max_phases,
                horizon_steps_per_phase=min(max_steps, 10),
            )
            return response, step_log
        except Exception:
            pass  # fall through to single-phase run

    try:
        response, step_log = _run_plan_loop(
            rain, goal, steps, step_log, history, max_steps, use_memory,
            approval_callback, memory_ctx, qpu_context_inject,
            save_persistent_task, clear_persistent_task,
            STATUS_IN_PROGRESS, STATUS_CANCELLED, start_index=1,
        )
        return response, step_log
    finally:
        rain.goal_stack.pop_goal()
