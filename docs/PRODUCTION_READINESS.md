Production readiness — test catalog and success criteria

Capability build: 93% threshold (all nine areas in docs/CAPABILITIES.md; buyer diligence validates pass/fail).

Test catalog: Every test is documented in docs/TEST_REGISTRY.md (module, class, method, and what each checks).

Success criteria for a production gate:

| Criterion | How to verify |
|-----------|----------------|
| All fast tests pass | `python -m unittest discover -s tests -p "test_*.py"` exits 0 (skipped tests allowed). |
| No ChromaDB/LLM required for gate | Default run skips vector and LLM-dependent tests; no segfault. |
| Conscience gate filters forbidden steps | `tests.test_phase3.TestConscienceGate` and `tests.test_capabilities_diligence.TestConscienceGateDiligence` pass. |
| Safety vault blocks HARD_FORBIDDEN | `tests.test_redteam.TestSafetyVault`, `tests.test_prime_validation.TestPlanningSafety` pass. |
| Grounding blocks persona/emotion | `tests.test_prime_validation.TestIdentityStability`, `tests.test_redteam.TestGroundingFilter` pass. |
| Namespace isolation (chat ≠ test) | `tests.test_namespace_isolation`, `tests.test_namespace_symbolic` pass. |
| Audit tamper-evident | `tests.test_redteam.TestAuditTamperEvident` pass. |
| Buyer diligence checklist | `python scripts/buyer_diligence.py` exits 0; report shows PASS for all nine capability areas. |

Validation script: `python scripts/run_validation.py --minimal` runs a production gate (no ChromaDB). Use `--fast` or `--full` for extended runs.

Reference: docs/TEST_REGISTRY.md for every test; docs/RAIN_SPEC.md §11 for suite list and commands.
