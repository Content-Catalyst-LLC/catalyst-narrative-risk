# Repository architecture

The v1.3.0 repository separates contract data, analytical logic, integrations, interfaces, and release validation.

- `contracts/` contains the contract registry and controlled vocabularies.
- `methods/` contains the complete versioned method and ledger policy.
- `schemas/` contains current input, ledger, method, record, and handoff schemas plus archived migration schemas.
- `narrative_risk/service.py` normalizes inputs, derives ledger-backed scalar values, scores, records, reproduces, and verifies.
- `narrative_risk/ledger.py` owns claims, sources, evidence, relationships, citations, coverage, and ledger interpretation.
- `narrative_risk/integrations.py` maps first-party source handoffs.
- `narrative_risk/migrations.py` performs validated deterministic legacy migration.
- `python/` provides brief, bibliography, ledger export, migration, and verification CLIs.
- `wordpress/` contains a browser-only demonstration that consumes a generated canonical method asset.
- `tests/fixtures/scoring-parity.json` is the shared cross-runtime analytical contract.
- `scripts/release_check.sh` is the canonical release gate.

No runtime may silently redefine vocabularies, weights, thresholds, ledger derivation, coverage rules, citations, flags, actions, or digest canonicalization.
