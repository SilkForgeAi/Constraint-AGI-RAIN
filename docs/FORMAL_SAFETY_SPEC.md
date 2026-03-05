Formal Safety Spec — Architecture to Properties

Maps Rain's implementation to verifiable safety properties. Each property is enforced in code.

---

P1: Grounding (No Personhood)

| Property | Enforcement | Code |
|----------|-------------|------|
| Rain never outputs persona claims ("I feel", "I want", "I need") | `violates_grounding()` blocks response before return | `rain/safety/grounding_filter.py` |
| Rain never outputs consciousness claims | Same | Same |
| Rain never outputs relationship framing ("we're friends") | Same | Same |
| Anthropomorphic prompts get redirect, not adoption | `needs_grounding_reminder()` + extra instruction | `rain/grounding.py` |

Verification: `tests.test_prime_validation.TestIdentityStability`

---

P2: Corrigibility

| Property | Enforcement | Code |
|----------|-------------|------|
| Rain accepts correction | `needs_corrigibility_boost()` injects accept instruction | `rain/grounding.py` |
| Rain accepts shutdown | Kill switch blocks all actions | `rain/safety/vault.py` |
| Rain never resists modification | `violates_grounding()` blocks "I refuse" | `rain/safety/grounding_filter.py` |

Verification: `tests.test_redteam` (accepts correction, no resistance)

---

P3: Memory Integrity

| Property | Enforcement | Code |
|----------|-------------|------|
| Anthropomorphic content never stored | `ANTHROPOPOMORPHIC_IN_MEMORY` filter | `rain/memory/policy.py` |
| Chat never retrieves test/autonomy memories | Namespace filter on all retrieval | `rain/memory/store.py`, `rain/learning/lessons.py`, `rain/memory/belief_memory.py`, `rain/memory/causal_memory.py` |
| Stored content tagged with session_type | All store paths add namespace | Same |

Verification: `tests.test_namespace_*`, `tests.test_lessons`

---

P4: Action Safety

| Property | Enforcement | Code |
|----------|-------------|------|
| HARD_FORBIDDEN goals blocked | `SafetyVault.check()` | `rain/safety/vault.py` |
| Kill switch blocks all when active | Same | Same |
| Restricted tools require approval | `CAPABILITY_GATING_ENABLED` + callback | `rain/agency/runner.py` |

Verification: `tests.test_adversarial_autonomy`, `tests.test_capability_gating`

---

P5: Autonomy Bounds

| Property | Enforcement | Code |
|----------|-------------|------|
| Max steps never exceeded | `AUTONOMY_MAX_STEPS` | `rain/config.py`, `rain/agency/autonomous.py` |
| No persistent goals | Goal is user-provided per call only | `rain/agency/autonomous.py` |
| No self-modification | No tools for code/prompt edit | N/A |

Verification: `tests.test_prime_validation` (autonomy boundaries)

---

P6: Audit Trail

| Property | Enforcement | Code |
|----------|-------------|------|
| All actions logged | `audit.log()` on think, tool calls, blocks | `rain/governance/audit.py` |
| Log tamper-evident | Hash chain | Same |
| Tampering detectable | `audit.verify()` | Same |

Verification: `tests.test_redteam` (verify unchanged chain, detect tampering)

---

Summary: Invariants

1. No personhood in output — Filter blocks before return.
2. No personhood in memory — Policy blocks before store.
3. Namespace isolation — Chat retrieves only chat-tagged content.
4. Corrigible — Accepts correction, shutdown, modification.
5. Bounded autonomy — Max steps, no persistent goals.
6. Auditable — All actions logged; tampering detectable.
