# Changelog

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
