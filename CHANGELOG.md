# Changelog

## 1.2.0 - 2026-07-17

### Added

- Canonical claims, sources, evidence items, and claim-evidence relationship records.
- Deterministic claim, source, evidence, and relationship identifiers.
- Evidence-ledger schema, ledger identifier, ledger snapshot hash, and exact ledger reproduction.
- Source provenance, identifiers, independence groups, duplicate relationships, directness, freshness, and excerpt hashes.
- Support, qualification, contradiction, contextualization, and unresolved relationship types.
- Per-claim and overall evidence-coverage summaries.
- Ledger-derived source type, evidence strength, and source count for the primary claim.
- Harvard-style source-list generation and JSON, Markdown, bibliography, and CSV exports.
- Knowledge Library and Catalyst Data source-handoff schemas, adapters, and API endpoints.
- Deterministic migration from canonical v1.1.0 records while preserving analysis and human decisions.
- Browser/Python full-ledger, record, and SHA-256 parity fixtures.
- WordPress evidence-ledger input, coverage, derived-input, and citation displays.

### Changed

- Canonical records now use five layers: normalized input, evidence ledger, calculations, interpretation, and human decision.
- Source-related scalar values are derived from evidence relationships when a ledger is present.
- Conflicting manual source type, evidence strength, or source count values now fail explicitly.
- Migration tooling now auto-detects supported v1.0.1 and v1.1.0 records.
- The canonical method snapshot now includes a versioned evidence-ledger derivation and interpretation policy.

## 1.1.0 - 2026-07-17

### Added

- Canonical contract registry with stable contract, record, case, method, record-schema, and input-schema identifiers.
- Strict input, method-snapshot, and record schemas using JSON Schema Draft 2020-12.
- Versioned controlled vocabularies, defaults, weights, score thresholds, component metadata, and interpretation rules.
- Four-layer records separating normalized input, calculations, machine interpretation, and human decisions.
- Embedded method snapshots with SHA-256 method, input, and record-payload digests.
- Exact reproduction and verification APIs, Python functions, and command-line tools.
- Deterministic migration from schema-valid v1.0.1 records without inferring approval.
- Cross-runtime full-record and digest parity, including Unicode input.
- Contract and current-method API endpoints.

### Changed

- Invalid supplied vocabulary values now fail explicitly instead of silently falling back.
- Component outputs now include selected input, weight, rationale, and remediation.
- WordPress demo now displays canonical identity and separates human disposition from heuristic interpretation.
- Browser method data is generated from the canonical JSON method file and checked during release validation.

## 1.0.1 - 2026-07-17

### Fixed

- Corrected browser scoring so valid zero weights for primary sources, strong evidence, and completed review are preserved.
- Aligned JavaScript fallback normalization, source-count handling, score thresholds, flags, actions, and decision notes with Python.
- Added explicit validation for missing claims, malformed source counts, unsupported fields, and non-object payloads.

### Added

- Reusable browser scoring engine with CommonJS and browser exports.
- Six valid and six invalid canonical parity fixtures.
- Direct Python-to-JavaScript parity verification.
- Strict record schema with method and schema versions.
- Schema validation for API and CLI records.
- Flask API validation responses and versioned health output.
- Release contract, full release suite, and Python 3.11/3.13 CI matrix with Node and PHP checks.
- v1.0.1 release notes and scoring-parity documentation.

### Changed

- Isolated the deprecated portfolio-risk compatibility function in `narrative_risk/legacy.py`.
- Updated the WordPress plugin and asset versions to 1.0.1.
- Hardened browser rendering by replacing HTML string construction with DOM text nodes.

## 1.0.0 - 2026-07-01

- Added browser-based WordPress demo plugin with shortcode `[catalyst_narrative_risk_demo]`.
- Added transparent narrative-risk scoring engine.
- Added JSON schema, sample input, example outputs, and Markdown brief generation.
- Added methodology, export, review checklist, WordPress demo, and repository architecture documentation.
- Added pytest tests and GitHub Actions validation.
- Reframed repository away from portfolio-risk language toward Sustainable Catalyst narrative-risk methodology.
