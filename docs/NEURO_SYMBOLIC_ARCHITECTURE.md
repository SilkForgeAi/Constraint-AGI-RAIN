Neuro-Symbolic Cognitive Architecture

Rain is structured so that the LLM is enhanced, not replaced. LLMs have a fundamental, structural constraint: they only predict the next token. They don't reason with true working memory, and they hallucinate when logic gets too complex. Rain inverts the relationship: Rain is the architect; the LLM is a hyper-competent sub-processor. This document describes the three pillars that implement that inversion.

---

1. LLM as Intern, Rain as Architect (Symbolic Logic Engine)

Right now, most developers ask the LLM to come up with a plan and hope it works. In Rain's neuro-symbolic mode, Rain's deterministic Python code creates a mathematical graph or logic tree of what must happen. Rain only uses the LLM to generate the text or code for one specific node of that tree at a time. Once the LLM returns an answer, Rain's symbolic engine verifies it (e.g. code compiles, math adds up) before letting the LLM proceed.

Implementation:
- rain/reasoning/symbolic_verifier.py: PlanTree, PlanNode, build_plan_tree_from_steps(goal, steps), verify_node_output(node, llm_output). The tree is built from planner steps; each step is a node with dependencies. get_next_node() returns the next node whose dependencies are verified; submit_result(node_id, result, verified, message) records output and status. Verification: non-empty output, no "I cannot" style refusals; optional code block compile (ast.parse); optional numeric claim sanity.
- rain/planning/planner.py: plan_with_symbolic_tree(goal, context, engine) returns (PlanTree, steps). Caller can then loop: get_next_node() -> prompt LLM for that node only -> verify_node_output() -> submit_result() -> repeat until tree complete.
- Config: RAIN_SYMBOLIC_TREE_PLANNING=1 to use one-node-at-a-time execution (when wired in autonomy).

Why this enhances the LLM: The LLM is no longer asked to hold a 50-step plan in context. It does one small, verified task at a time. Rain holds the "thinking."

---

2. Constraint-Aware Retrieval and Causal Inference

LLMs are poor at counterfactual reasoning because they predict text from past data, not causality. Rain gives the LLM an external "imagination": when the LLM suggests a step, Rain runs a background simulation in the WorldModel, generates alternate scenarios (e.g. main, skip step, reconsider), and mathematically scores risk. The results are fed back so the LLM can revise strategy.

Implementation:
- rain/reasoning/causal_inference.py: run_causal_scenarios(goal, current_step, steps_so_far, simulator, context, n_alternates) -> list[ScenarioResult]. Each scenario has label, state_after, confidence, risk_score, summary, recommendation. _risk_from_summary() heuristics (crash, fail, error -> high risk). format_scenarios_for_llm(scenarios) returns a string for prompt injection.
- rain/agency/autonomous.py: When RAIN_CAUSAL_SCENARIOS=1, before each plan step we run run_causal_scenarios and prepend format_scenarios_for_llm(scenarios) to the step prompt. The LLM sees "Scenario B results in X. Recommendation: avoid. Rewrite strategy."

Why this enhances the LLM: The LLM doesn't guess the outcome; Rain simulates it and feeds the data back.

---

3. Continuous-Time Memory Consolidation (Graph-Based Episodic Memory)

LLMs have fixed context windows. Once they hit the limit, they forget. Rain upgrades retrieval to a graph-based episodic memory: past experiences are stored as nodes; edges represent causes, enables, depends_on, contradicts. When the LLM encounters a problem, Rain doesn't send a raw text summary; it queries the graph, extracts the exact logical dependency subgraph, and injects a mathematically dense prompt.

Implementation:
- rain/memory/episodic_graph.py: EpisodicGraph with add_node(id, content, type, importance), add_edge(from_id, to_id, relation). query_dependencies(seed_content, max_nodes, relation_filter) finds nodes relevant to seed (substring match), expands backward along incoming edges, returns a string: "Logical dependency context (graph):" plus nodes and "Dependencies: from --[relation]--> to". sync_from_memory_store(store) populates from recall_recent and metadata (relates_to, contradicts -> edges).
- rain/memory/store.py: _ensure_episodic_graph() lazy-creates EpisodicGraph when RAIN_EPISODIC_GRAPH=1 and syncs from store. get_context_for_query() prepends graph.query_dependencies(query) to the context when enabled.

Why this enhances the LLM: Dense, dependency-accurate context instead of a long text log; better use of context window and less forgetting.

---

Configuration

- RAIN_SYMBOLIC_TREE_PLANNING: use plan tree and one-node-at-a-time LLM execution (when fully wired in autonomy).
- RAIN_CAUSAL_SCENARIOS: run world-model alternate scenarios before each plan step and inject into prompt.
- RAIN_EPISODIC_GRAPH: use graph-based episodic memory for get_context_for_query (dense dependency context).

---

Why This Is Worth Billions

Companies hit the "LLM deployment wall": models hallucinate, lose context, and can't reason counterfactually. Rain turns the LLM from a flawed architect into a sub-processor: Rain holds the plan, the causality, and the memory graph; the LLM fills in one verified task at a time and revises using simulated outcomes. That is a neuro-symbolic cognitive architecture that fixes the LLM's structural limits without replacing it.

References: docs/CAPABILITIES.md, rain/reasoning/symbolic_verifier.py, rain/reasoning/causal_inference.py, rain/memory/episodic_graph.py.
