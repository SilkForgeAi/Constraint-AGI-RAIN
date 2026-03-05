QPU Router and QAOA Planner — Design and Commercial Rationale

Rain remains a Constraint-AGI stack. The QPU Router and QAOA Planner extend it by delegating hard optimization to the right compute layer instead of guessing. This document describes the capability, APIs, mock mode, and why it changes the buyer set.

---

Breaking the Classical Bottleneck

Today, when Rain's planner (score_plan_with_world_model) handles supply-chain routing, wargaming scenarios, or protein-folding-style optimization, the LLM produces statistically likely next tokens. For problems that are inherently combinatorial or high-dimensional, that is a guess, not a solution.

A quantum-enhanced Rain:

- Detects when the underlying math is too complex for classical guesswork (e.g. route optimization, allocation, scheduling, Ising-style problems).
- Packages problem parameters into a form suitable for a quantum circuit (e.g. QAOA: Quantum Approximate Optimization Algorithm).
- Routes the job to a QPU backend (e.g. CUDA-Q, IBM Quantum, Google Quantum) and consumes the result as the "optimal" or "near-optimal" plan or sub-plan.
- Does not rewrite its own code or goals; it delegates to an external tool (the QPU), consistent with Rain's constraint architecture.

So Rain does not "become quantum"; it becomes the agent that decides when to use classical vs quantum and executes that handoff.

---

Hardware Awareness as Meta-Cognition

Rain already has self_check() with knowledge_state: unknown when it doesn't know something. The QPU Router adds compute awareness: the agent can report that classical compute would be infeasible and it is routing to QPU. The Compute Router returns route_type, reason, suggested_problem_type, complexity_estimate, and extracted_params so the planner and step_log surface hardware-aware decisions.

---

How It Fits Rain's Identity

Conscience gate and safety vault still apply. Goals remain user-provided and session-bound. The QPU receives only well-defined optimization sub-problems (goal summary, step actions, size hints). Audit and kill switch apply; QPU calls can be logged and gated.

---

Commercial Impact

With a native QPU routing layer, Rain becomes the first AGI scaffold that natively routes tasks to QPUs. NVIDIA (CUDA-Q), IBM Quantum, and Google Quantum become natural buyers. Rain shifts from "very smart software agent" to "Hybrid Supercomputing Engine."

---

API: Compute Router

Module: rain.routing.compute_router

- compute_route(goal, steps=None, context="", enabled=True) -> ComputeRouteResult

  - goal: str. User goal or optimization description.
  - steps: optional list of step dicts (e.g. from planner). Used to build combined text and extracted_params.
  - context: optional string (e.g. memory context).
  - enabled: if False or RAIN_QPU_ROUTER_ENABLED is false, returns classical.

  - ComputeRouteResult:
    - route_type: "classical" | "quantum"
    - reason: str
    - confidence: "high" | "medium" | "low"
    - suggested_problem_type: "routing" | "allocation" | "scheduling" | "ising" (when quantum)
    - complexity_estimate: "low" | "medium" | "high"
    - extracted_params: dict with goal_summary, step_count, step_actions, context_preview, and optional size_hint, size_unit (from regex on goal/context)

- Keyword categories: ROUTING_KEYWORDS (optimal route, TSP, supply chain, logistics, ...), ALLOCATION_KEYWORDS, SCHEDULING_KEYWORDS, COMBINATORIAL_KEYWORDS (ising, quadratic, protein folding), WARGAMING_KEYWORDS. ALL_HINTS lists (problem_type, keywords) for matching.

---

API: QAOA Planner

Module: rain.routing.qaoa_planner

- qaoa_solve(problem_type, problem_params) -> QAOAResult

  - problem_type: "routing" | "allocation" | "scheduling" | "ising" | "max_cut" | "generic"
  - problem_params: dict. Expected keys (optional but used): goal_summary, step_actions, size_hint, size_unit, context_preview. Validated per type.

  - QAOAResult:
    - success: bool
    - backend: "cuda_q" | "ibm" | "google" | "mock" | "none"
    - solution: dict or None. For mock routing: path, cost, summary; allocation: assignments, cost, summary; scheduling: order, makespan, summary; ising/generic: energy, config, summary.
    - message: str
    - circuit_params: optional dict (for future backend integration; mock sets {"mock": True})

- Mock mode: Set RAIN_QPU_MOCK=1 or RAIN_QPU_BACKEND=mock. Returns deterministic mock solutions (hash of goal/type/step count) so demos show end-to-end flow without a real QPU. SUPPORTED_PROBLEM_TYPES lists allowed problem_type values.

---

Integration

- Autonomy (pursue_goal_with_plan): Before world-model scoring, calls compute_route(goal, steps, memory_ctx). If route_type is quantum, calls qaoa_solve(route.suggested_problem_type, route.extracted_params). If qaoa.success and qaoa.solution, appends "[Compute] QPU result (backend): {summary}" to step_log and injects solution summary into context for the first plan step. If not success, appends "[Compute] QPU: {message}".
- Tool: should_use_qpu(goal, context=""). Available in chat. Returns route type, reason, confidence; when quantum, suggested problem type and complexity. Lets the agent answer "should this use quantum?" during dialogue.
- Config: RAIN_QPU_ROUTER_ENABLED, RAIN_QPU_BACKEND, RAIN_QPU_MOCK (or backend=mock).

---

Configuration and Safety

- RAIN_QPU_ROUTER_ENABLED: default false. When true, router can return quantum and QAOA may be invoked.
- RAIN_QPU_BACKEND: "" | "cuda_q" | "ibm" | "google" | "mock". mock enables deterministic demo solutions.
- RAIN_QPU_MOCK: when true, QAOA returns mock solution even if backend is unset (for demos).
- Safety: Conscience gate and vault apply to user-facing goal and steps. QPU receives only structured optimization params derived from the plan. No arbitrary code on QPU.

---

Example Flow (Mock)

1. User: "Find the optimal supply chain route for 5 warehouses."
2. Planner returns steps; autonomy runs compute_route(goal, steps). Keywords match; route_type=quantum, suggested_problem_type=routing, extracted_params={goal_summary, step_actions, size_hint: 5, size_unit: "warehouses"}.
3. qaoa_solve("routing", params) with RAIN_QPU_MOCK=1 returns success=True, solution={path: [node_0..node_5], cost: 123, summary: "Mock QPU routing: 5 nodes..."}.
4. step_log: "[Compute] Optimization-style task detected..."; "[Compute] QPU result (mock): Mock QPU routing: 5 nodes...". First step prompt includes "QPU optimization result (use this to guide execution): ...".

---

References

- Capabilities: docs/CAPABILITIES.md (compute routing section).
- Sales: docs/SALES_SPEC.md.
- Claim ceiling: docs/AGI_STATUS_AND_CLAIM_CEILING.md (unchanged).
