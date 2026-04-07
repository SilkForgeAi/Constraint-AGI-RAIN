"""
Cross-domain analogy retrieval — find structurally similar problems from other domains
in memory. This is where novel insights come from: a solved problem in domain A may
directly transfer to an unsolved problem in domain B.

Called from _build_memory_context() alongside standard similarity retrieval.
Results are injected as context so the LLM can reason by analogy across fields.
"""
from __future__ import annotations

import re
from typing import Any

# Domain taxonomy — heuristic keyword mapping
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "biology": [
        "cell", "organism", "evolution", "gene", "protein", "neural", "brain",
        "immune", "dna", "rna", "species", "mutation", "ecosystem",
    ],
    "physics": [
        "energy", "force", "wave", "quantum", "entropy", "thermodynamic",
        "momentum", "field", "particle", "resonance", "oscillat", "gravity",
    ],
    "economics": [
        "market", "price", "supply", "demand", "incentive", "trade", "cost",
        "utility", "equilibrium", "arbitrage", "inflation", "capital",
    ],
    "engineering": [
        "system", "circuit", "component", "load", "fault", "redundancy",
        "latency", "throughput", "bandwidth", "pipeline", "protocol",
    ],
    "mathematics": [
        "proof", "theorem", "equation", "algebra", "topology", "manifold",
        "gradient", "integral", "discrete", "combinatorial", "eigenvalue",
    ],
    "psychology": [
        "behavior", "cognition", "emotion", "motivation", "bias", "heuristic",
        "attention", "perception", "reinforcement", "anchoring",
    ],
    "logistics": [
        "route", "schedule", "deliver", "fleet", "warehouse", "inventory",
        "fulfillment", "lead time", "throughput", "capacity planning",
    ],
    "social": [
        "coordination", "cooperation", "trust", "norm", "institution",
        "collective", "governance", "consensus", "signaling",
    ],
    "chemistry": [
        "reaction", "catalyst", "bond", "molecule", "synthesis", "solvent",
        "concentration", "equilibrium", "oxidation", "reduction",
    ],
    "computer_science": [
        "algorithm", "complexity", "recursion", "graph", "hash", "cache",
        "concurrency", "abstraction", "interface", "polymorphism",
    ],
}

# Structural/relational verbs and abstractions that signal problem shape
_STRUCTURAL_VERBS: frozenset[str] = frozenset({
    "optimize", "minimize", "maximize", "balance", "coordinate", "distribute",
    "allocate", "propagate", "cascade", "feedback", "iterate", "converge",
    "decompose", "compose", "abstract", "generalize", "constrain", "bound",
    "route", "schedule", "prioritize", "rank", "cluster", "classify",
    "predict", "infer", "detect", "filter", "aggregate", "transform",
    "encode", "decode", "compress", "expand", "merge", "partition",
    "stabilize", "regulate", "adapt", "evolve", "prune", "select",
})


def _detect_domain(text: str) -> str | None:
    """Heuristically detect the primary domain of a text snippet."""
    lower = (text or "").lower()
    best_domain: str | None = None
    best_score = 0
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain if best_score >= 2 else None


def _structural_keywords(text: str) -> frozenset[str]:
    """Extract structural/relational keywords for cross-domain matching."""
    words = frozenset(re.findall(r"[a-z]{4,}", (text or "").lower()))
    return words & _STRUCTURAL_VERBS


def find_cross_domain_analogies(
    memory: Any,
    prompt: str,
    top_k: int = 3,
    namespace: str | None = None,
) -> list[dict]:
    """
    Search memory for experiences/skills from a DIFFERENT domain that share
    structural similarity with the current prompt.

    Returns list of dicts:
      {content, domain, shared_structure, relevance_note}
    sorted by structural overlap score descending.
    """
    prompt_domain = _detect_domain(prompt)
    prompt_struct = _structural_keywords(prompt)
    if not prompt_struct:
        return []

    # Pull a broad candidate set
    try:
        candidates_raw = memory.get_context_for_query(
            prompt, max_experiences=25, namespace=namespace
        )
    except Exception:
        return []

    if not candidates_raw:
        return []

    # Split into individual chunks
    chunks = [c.strip() for c in re.split(r"\n{2,}", candidates_raw) if c.strip()]

    scored: list[tuple[float, dict]] = []
    for chunk in chunks[:35]:
        chunk_domain = _detect_domain(chunk)
        # Only surface cross-domain matches
        if not chunk_domain or chunk_domain == prompt_domain:
            continue
        chunk_struct = _structural_keywords(chunk)
        if not chunk_struct:
            continue
        shared = prompt_struct & chunk_struct
        if not shared:
            continue
        score = len(shared) / max(len(prompt_struct), 1)
        if score >= 0.15:
            scored.append((score, {
                "content": chunk[:300],
                "domain": chunk_domain,
                "shared_structure": sorted(shared)[:5],
                "relevance_note": (
                    f"Pattern from {chunk_domain}: "
                    + ", ".join(sorted(shared)[:3])
                ),
            }))

    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:top_k]]


def format_analogies_for_context(analogies: list[dict]) -> str:
    """Format cross-domain analogies as a compact context block."""
    if not analogies:
        return ""
    lines = [
        "[Cross-domain analogies — structurally similar patterns from other fields "
        "(use these to reason by analogy and surface non-obvious approaches):"
    ]
    for a in analogies:
        lines.append(
            f"  [{a['domain'].upper()}] {a['content'][:220]}"
            + (f" ({a['relevance_note']})" if a.get("relevance_note") else "")
        )
    lines.append("]")
    return "\n".join(lines)
