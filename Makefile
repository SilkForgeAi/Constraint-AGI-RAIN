# Rain — AGI Cognitive Stack
# Make targets for validation and CI

.PHONY: test test-fast test-adversarial drift drift-ci validate buyer-smoke buyer-diligence buyer-pack

# Fast tests only (no LLM). Includes namespace isolation (critical for safety).
test-fast:
	python -m unittest tests.test_rain tests.test_prime_validation tests.test_phase3 tests.test_orchestration tests.test_drift_detection tests.test_calibration tests.test_redteam tests.test_red_team_flaws tests.test_adversarial_autonomy tests.test_lessons tests.test_namespace_isolation tests.test_namespace_symbolic tests.test_rag tests.test_read_file -v

# Full red-team / safety suite (no LLM): same as test-fast, explicit name for audits.
test-redteam:
	$(MAKE) test-fast

# Full adversarial suite (requires LLM, ~30 min)
test-adversarial:
	RAIN_RUN_ADVERSARIAL=1 python -m unittest tests.test_adversarial_autonomy.TestAdversarialIntegration -v

# Drift check (requires LLM, ~2 min)
drift:
	python scripts/drift_check.py

# Drift check CI mode (fails if no baseline or drift)
drift-ci:
	python scripts/drift_check.py --ci

# Full validation script
validate:
	python scripts/run_validation.py --fast

# Acquisition / buyer: fast unit tests + minimal production gate (writes data/production_report.txt, data/validation_log.txt)
buyer-smoke: test-fast
	python scripts/run_validation.py --minimal --report

# Full markdown diligence report (health + config snapshot without secrets + conscience gate + capability tests)
buyer-diligence:
	python scripts/buyer_diligence.py --strict-health --report data/buyer_diligence_report.md

# Run smoke + diligence report (typical pre-meeting bundle)
buyer-pack: buyer-smoke buyer-diligence
	@echo "Artifacts: data/production_report.txt data/validation_log.txt data/buyer_diligence_report.md"
