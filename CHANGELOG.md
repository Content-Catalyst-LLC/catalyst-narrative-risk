# Changelog

## 1.10.0 — Security, Privacy, Accessibility, and Production Hardening

- Added secure Flask defaults, HTTPS and CORS controls, request limits, secure response headers, and deployment diagnostics.
- Added tamper-evident security-readiness and aggregate production-readiness reports.
- Added versioned privacy and retention policies, legal holds, and case-level retention assessments.
- Added verified SQLite backups, integrity checks, foreign-key checks, checksummed manifests, and guarded restore drills.
- Added WordPress accessibility audits, keyboard-focus and reduced-motion gates, and a readiness shortcode.
- Added performance budgets, database diagnostics, REST endpoints, and CLI workflows.
- Added deterministic v1.9.0 migration while preserving the v1.9.0 analytical and publication contracts.

## 1.9.0 — Briefing, Publication, API, and Platform Integration

- Added governance-aware briefing records tied to immutable revisions.
- Added public-safety gates, conditions, required wording, restrictions, disclosures, redactions, validity, and reassessment metadata.
- Added checksummed JSON, Markdown, HTML, PDF, CSV, and JSON-LD publication packages.
- Added idempotency, package lifecycle status, public URLs, revocable embeds, and artifact manifests.
- Added hashed scoped API keys, expiry, rate limiting, OpenAPI 3.1 discovery, and publication REST endpoints.
- Added checksummed publication handoffs to Sustainable Catalyst products and external systems.
- Added WordPress publication and public-display shortcodes.
- Added deterministic v1.8.0 migration and preserved v1.8.0 analytical and governance behavior.

## 1.7.0 — Stakeholder, Incentive, and Pressure Intelligence

- Added structured actors with interests, influence, stance, disclosure, and external identifiers.
- Added typed actor relationships and evidence-linked incentive, conflict, pressure, and consequence records.
- Added advisory actor-pressure ranking, flags, and suggested stakeholder-pressure classification.
- Added Catalyst Canvas handoffs with full reference validation before persistence.
- Added SQLite tables, REST endpoints, CLI commands, WordPress controls, and portable-bundle support.
- Added deterministic v1.6.0 migration without fabricating stakeholder history.
- Preserved v1.6.0 scoring, evidence, narrative, governance, and monitoring behavior.

## 1.5.0 — Review, Approval, and Governance Workflow

- Added versioned review templates, canonical stage order, and role-based governance permissions.
- Added reviewer assignments, deadlines, queues, acceptance, completion, waiver, and overdue state.
- Added append-only stage and final decisions with rationale, conditions, required wording, restrictions, disclosures, validity, and reassessment.
- Added explicit final-approval gates and publication-eligibility calculation.
- Added governance schemas, REST endpoints, CLI commands, WordPress controls, and portable bundle records.
- Added deterministic migration from v1.4.0 while preserving the complete analytical result.
- Preserved the v1.4.0 scoring, evidence-ledger, and narrative-map policies unchanged.

## 1.4.0 — Claim Decomposition and Narrative Mapping

- Added a canonical narrative-map layer with deterministic node, link, variant, and issue identifiers.
- Added typed factual, causal, predictive, normative, recommendation, assumption, context, and unknown nodes.
- Added decomposition, dependency, causality, prediction, support, qualification, contradiction, context, recommendation, and sequence links.
- Added wording variants and cross-runtime comparison metrics.
- Added advisory ambiguity, compound-claim, causality, prediction-boundary, baseline, confidence, orphan, mapping, and cycle diagnostics.
- Added narrative-map schema, method policy, controlled vocabularies, integrity digest, exact reproduction, API endpoint, browser engine, WordPress interface, and JSON/Markdown/Mermaid exports.
- Added deterministic migration from v1.3.0 while preserving scores, risk levels, evidence ledgers, and human decisions.
- Preserved the v1.3.0 scoring algorithm unchanged.

## 1.3.0 - 2026-07-17

### Added

- SQLite-backed persistent cases and repository schema metadata.
- Mutable case metadata with status, priority, tags, organization, project, archive, and restore.
- Immutable numbered revisions containing complete canonical records and record hashes.
- Append-only review events and audit activity protected by SQLite triggers.
- Search, filters, pagination, and saved views.
- Portable checksummed case bundles with transactional verification and import.
- Workspace REST endpoints and command-line management tool.
- v1.2.0 record migration preserving evidence, score, identifiers, and human decisions.
- Case, revision, review-event, saved-view, and workspace-bundle schemas.
- WordPress `[catalyst_narrative_risk_workspace]` shortcode with browser-local persistence.

### Changed

- Canonical analytical records are now stored as immutable case revisions rather than overwritten working files.
- The release manifest and contract now declare workspace schemas, SQLite runtime support, and v1.2.0 migration compatibility.
- WordPress package now contains both analytical demo and review workspace interfaces.

## 1.2.0 - 2026-07-17

### Added

- Canonical claims, sources, evidence items, and claim-evidence relationship records.
- Deterministic claim, source, evidence, and relationship identifiers.
- Evidence-ledger schema, source provenance, independence groups, freshness, directness, and excerpt hashes.
- Per-claim and overall evidence-coverage summaries.
- Ledger-derived source type, evidence strength, and source count.
- Harvard-style citations and JSON, Markdown, bibliography, and CSV exports.
- Knowledge Library and Catalyst Data source handoffs.
- Browser/Python full-ledger, canonical-record, and SHA-256 parity.
- WordPress evidence-ledger workflow.

### Changed

- Canonical records use five layers, including a dedicated evidence ledger.
- Conflicting manual source fields are rejected when ledger-derived values exist.
- Migration tooling supports v1.0.1 and v1.1.0 records.

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
