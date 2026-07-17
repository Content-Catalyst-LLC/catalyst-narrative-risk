# Changelog

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
