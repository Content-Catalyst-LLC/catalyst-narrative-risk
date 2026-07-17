# Repository architecture

The v1.0.1 repository separates runtime responsibilities:

- `narrative_risk/service.py` is the canonical Python scoring and validation engine.
- `narrative_risk/legacy.py` isolates the deprecated portfolio compatibility shim.
- `assets/narrative-risk-engine.js` is the reusable browser scoring engine.
- `assets/catalyst-narrative-risk-demo.js` handles only browser form and rendering behavior.
- `tests/fixtures/scoring-parity.json` is the shared analytical contract.
- `scripts/cross_runtime_parity.py` compares Python and JavaScript outputs directly.
- `schemas/narrative_risk_record.schema.json` defines the export contract.
- `scripts/release_check.sh` is the canonical release gate.

No interface runtime may silently redefine weights, thresholds, normalization, flags, actions, or decision notes.
