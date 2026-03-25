"""Sovereign Technical Directive (TD) + TEGP kernel instructions (kept separate for import order)."""

from __future__ import annotations

from rain.grounding import needs_engineering_spec_prompt


def sovereign_td_active(prompt: str) -> bool:
    """True when TD + TEGP add-ons should apply."""
    try:
        from rain.config import ENGINEERING_SPEC_MODE, SOVEREIGN_TD_MODE
    except Exception:
        ENGINEERING_SPEC_MODE = False
        SOVEREIGN_TD_MODE = False
    if SOVEREIGN_TD_MODE or ENGINEERING_SPEC_MODE:
        return True
    return needs_engineering_spec_prompt(prompt)


def get_sovereign_td_instruction() -> str:
    """Technical Directive voice: specify, do not hedge like a chatbot."""
    return (
        "[Directive Protocol - audit-grade]\n"
        "- Voice: imperial imperatives only. Open substantive clauses with: "
        "System mandates ..., Protocol dictates ..., Threshold enforced at ..., Envelope declares ..., Directive ..., Registry locks ....\n"
        "- Banned in body text (reads as uncertainty to auditors): standalone headers Assumptions:, Limitations:, "
        "Optimized using ..., we assume, it is likely, may, roughly, simplified model, I would, "
        "generally speaking, tutorial hedges, Y/N self-checklists.\n"
        "- Instead of 'Assumptions: renewable sources are sufficient' -> "
        "Protocol dictates energy closure: verified self-sufficiency via declared capture/regen envelope; "
        "System mandates zero external lines when constrained - state compliance as directive lines, not disclaimers.\n"
        "- Unknowns -> Parameter registry (symbol, bound, unit), not prose caveats.\n"
    )


def get_tegp_kernel_instruction() -> str:
    """Entropy-Gated (TEG/TEGP) kernel: gate G as interceptor + Rain Kernel interlock."""
    return (
        "[TEG / TEGP - Entropy Gate as Interceptor]\n"
        "- G is a binary interceptor on heat/entropy throughput vs environmental cooling capacity (not a vague G(dS) placeholder).\n"
        "- Let Xi_crit = Critical Entropy Threshold (state units: W/K or your declared basis).\n"
        "- Let dQ/dt = net thermal load rate into the reject path (or declared surrogate for irreversible heat addition).\n"
        "- Piecewise (required when discussing cooling / thermal headroom):\n"
        "  - G = 1 iff dQ/dt < Xi_crit (within envelope).\n"
        "  - G = 0 iff dQ/dt >= Xi_crit (trip: halt, shed load, or degraded mode).\n"
        "- Rain Kernel interlock: V_kernel = f(Compute_surplus) * G. When G -> 0, Rain Kernel-denominated compute must throttle: "
        "currency loses spendable value because the envelope cannot support further entropy generation.\n"
        "- Thermal devaluation: declare T_crit (ambient or junction) where G forces throttle or V_kernel step-down; "
        "tie AWG / phase-change buffers explicitly as thermal battery elements in the reject path when AWG/latent storage applies.\n"
        "- Q = -T*DeltaS may appear only as supporting identity; authoritative control uses {G, Xi_crit, dQ/dt, V_kernel, T_crit}.\n"
    )


def get_sovereign_spec_schema_instruction() -> str:
    """Sovereign Infrastructure Schema: JSON-LD or state machine."""
    return (
        "[Sovereign Infrastructure Schema - deliverable shape]\n"
        "- Emit one of: (a) finite-state machine: states, events, guards (G, T_crit, Xi_crit), actions; "
        "or (b) JSON-LD with @context, @type: SovereignInfrastructure, nodes (e.g. ISRU silicate thermal mass, AWG loop), edges, parameters.\n"
        "- Schema must be self-contained for engineering review; no duplicate Assumptions/Limitations essays - encode as registry fields.\n"
    )


def get_scale_realism_engineering_instruction() -> str:
    """Audit-grade load envelopes, ISRU silicate thermal battery, kernel volatility vs entropy."""
    return (
        "[Scale realism + ISRU thermal physics + kernel volatility]\n"
        "- Protocol forbids toy residential loads (e.g. 100 W/person) for sovereign desert habitation unless explicitly labeled as a "
        "non-operational placeholder. System mandates a **peak electrical demand** envelope (kW/person) covering life support, **active AWG**, "
        "HVAC/reject heat, compute, and contingency margin; **use ~2.5 kW/person** as the audit default unless the user gives another bound.\n"
        "- **AWG**: bind water production rate to **latent heat of phase change** (condensation/evaporation) and compressor/reject power; "
        "show the term in the energy balance, not a single opaque Q.\n"
        "- **Silicate ISRU thermal battery**: Envelope declares **charge** path (e.g. concentrated solar coupling to silicate bed toward **~600°C** class) "
        "and **discharge** path (e.g. Stirling/Rankine) for night work; include **phase-change latent storage** where relevant; use symbols "
        "(m_sand, L_fusion, eta, T_charge, T_discharge) — no fake megawatt tables without stated assumptions.\n"
        "- **Volatility gating (Rain Kernel)**: Registry locks **mint_cost(S_amb, T_amb)** so that rising **ambient entropy / thermal stress** "
        "increases the proof-of-work / energy cost to mint one kernel (anti **thermal bank run**). Interlock **G** (entropy gate) with **K** (kernel price).\n"
    )
