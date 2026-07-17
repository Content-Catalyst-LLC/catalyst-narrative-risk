# Catalyst Narrative Risk Build Map

## Product direction

Catalyst Narrative Risk should become the Sustainable Catalyst platform's structured claims, evidence, uncertainty, narrative-change, and review-governance layer.

Its purpose is not to determine truth automatically. It should help people make the review path visible: what is being claimed, what evidence supports or qualifies it, what assumptions remain, which stakeholders or incentives may shape interpretation, how the narrative is changing, what the consequences of overstatement are, and who approved the claim for a particular use.

## Current baseline — v1.0.0

The repository already provides a strong inspectable foundation:

- Deterministic Python heuristic scoring.
- Claim, source type, evidence strength, uncertainty, volatility, pressure, time sensitivity, consequence, review status, and source-count inputs.
- Risk score, risk level, component weights, flags, actions, and decision note.
- JSON and Markdown generation.
- JSON Schema, sample fixtures, methodology documentation, and review checklist.
- Client-side WordPress shortcode demo.
- GitHub Actions and five passing tests.

The current implementation is still a single-record demonstration. It does not yet provide a canonical versioned scoring contract, structured source and evidence records, persistent cases, claim relationships, review assignments, revision history, monitoring, organizational governance, or platform integrations.

## Release roadmap

### v1.0.1 — Scoring Parity and Release Integrity

Repair the existing foundation before expanding it.

- Fix Python/JavaScript scoring differences caused by JavaScript fallback expressions that replace valid zero weights.
- Use explicit key-existence checks rather than truthy fallbacks.
- Add shared high-, medium-, low-, and threshold-boundary fixtures.
- Run the same fixtures through Python and JavaScript and require identical outputs.
- Validate generated records against the JSON Schema in tests and CI.
- Add version consistency checks across the Python package, manifest, WordPress header, assets, documentation, and changelog.
- Add PHP syntax checks and JavaScript syntax/parity checks to CI.
- Add input error handling for invalid source counts, missing claims, unexpected values, and malformed JSON.
- Mark the legacy portfolio-risk compatibility shim deprecated and isolate it from the narrative-risk contract.
- Add a release contract script and reproducible release checklist.

**Release gate:** identical canonical outputs across Python, browser, CLI, examples, and schema validation.

### v1.1.0 — Canonical Narrative Risk Contract and Method Engine

Turn the heuristic prototype into a stable, versioned platform contract.

- Add canonical input and output schemas.
- Add `record_id`, `case_id`, `method_id`, `method_version`, `schema_version`, `created_at`, `updated_at`, and `created_by` fields.
- Define controlled vocabularies for sources, evidence, uncertainty, volatility, pressure, consequence, and review status.
- Separate raw inputs, normalized inputs, component calculations, final interpretation, and human review decisions.
- Move scoring weights and thresholds into a versioned method definition.
- Preserve method snapshots so old records remain reproducible after future changes.
- Add explanatory component metadata: rationale, maximum contribution, and remediation guidance.
- Add calibration fixtures and threshold tests.
- Establish backward-compatible migration rules for v1.0.0 exports.

**Release gate:** any record can be independently reproduced using its stored schema and method versions.

### v1.2.0 — Claims, Sources, and Evidence Ledger

Replace source counts with reviewable evidence relationships.

- Add structured claim records with scope, subject, geography, timeframe, audience, intended use, and confidence language.
- Add source records with title, author, publisher, URL, DOI or identifier, publication date, access date, source class, and provenance.
- Add evidence records with excerpts, notes, location pointers, attachments, and reviewer interpretation.
- Model evidence relationships as `supports`, `qualifies`, `contradicts`, `contextualizes`, or `does_not_resolve`.
- Track source independence, duplication, recency, directness, and primary-versus-secondary status.
- Add source-quality and evidence-coverage summaries without presenting them as truth judgments.
- Add citations and exportable source lists.
- Support imports from Knowledge Library and Catalyst Data contracts.

**Release gate:** every material risk conclusion can be traced to specific claims, sources, evidence items, and method rules.

### v1.3.0 — Persistent Cases and Review Workspaces

Move from generated files to durable working records.

- Add a repository layer with SQLite for portable use and PostgreSQL compatibility for production.
- Add organizations, workspaces, projects, cases, claims, sources, evidence, reviews, and revisions.
- Add create, read, update, archive, restore, and search operations.
- Add draft autosave, duplicate detection, tags, filters, and saved views.
- Add append-only history for scoring changes, evidence changes, and review decisions.
- Add import and export bundles with checksums and migration support.
- Add a REST API and a production WordPress interface backed by the canonical service rather than duplicated browser logic.
- Retain an optional private local-only demo mode.

**Release gate:** a case can be created, revised, closed, exported, re-imported, and reproduced without losing provenance.

### v1.4.0 — Claim Decomposition and Narrative Mapping

Support complex narratives rather than treating every statement as one undivided claim.

- Decompose compound statements into atomic claims, assumptions, causal links, forecasts, value judgments, and recommendations.
- Add parent-child and dependency relationships between claims.
- Track entities, events, places, dates, quantities, baselines, and comparison groups.
- Distinguish descriptive, causal, predictive, normative, reputational, and strategic claims.
- Add ambiguity, overbreadth, missing-baseline, unsupported-causality, and confidence-language flags.
- Add narrative variants and wording comparisons.
- Visualize claim maps, evidence coverage, unresolved assumptions, and contradiction or qualification paths.
- Permit human editing of all machine-assisted decomposition.

**Release gate:** reviewers can trace a public narrative from its headline statement to atomic claims, assumptions, and evidence coverage.

### v1.5.0 — Review, Approval, and Governance Workflow

Turn narrative-risk analysis into an accountable institutional process.

- Add reviewer assignments, due dates, comments, mentions, and review queues.
- Add workflow states: draft, evidence review, domain review, editorial review, legal/compliance review, approved with conditions, approved, rejected, superseded, and expired.
- Add decision records that distinguish the heuristic score from the human disposition.
- Add conditional approval, required wording, prohibited wording, disclosure requirements, and publication constraints.
- Add role-based permissions and separation of author, reviewer, and approver duties.
- Add review templates for research, public communications, sustainability reporting, policy, media, and decision support.
- Add escalation rules based on consequence, uncertainty, source weakness, or policy requirements.
- Add review expiration and mandatory re-review dates.

**Release gate:** every approved narrative has an identifiable reviewer, decision, date, conditions, and complete audit trail.

### v1.6.0 — Narrative Change, Freshness, and Monitoring

Make time and change first-class review dimensions.

- Add source freshness policies and per-claim review intervals.
- Store narrative snapshots and calculate score, evidence, and wording changes between revisions.
- Add narrative drift, confidence drift, source decay, and unresolved-change indicators.
- Connect claims to events and new evidence.
- Add watchlists, scheduled reassessment, alert rules, and notification records.
- Distinguish source updates from interpretation changes and stakeholder-pressure changes.
- Add timeline views for claims, sources, scores, reviews, and publication decisions.
- Add monitoring handoffs from Site Intelligence while retaining human review before changing a case disposition.

**Release gate:** the system can explain what changed, when it changed, which evidence caused the change, and whether a prior approval remains valid.

### v1.7.0 — Stakeholder, Incentive, and Pressure Intelligence

Expand stakeholder pressure from a single dropdown into an inspectable model.

- Add stakeholder and actor records with roles, interests, influence, exposure, dependencies, and public positions.
- Add pressure channels: financial, political, reputational, operational, legal, social, and internal governance.
- Record incentives, conflicts, disclosures, funding relationships, and information asymmetries.
- Map who creates, amplifies, contests, depends on, benefits from, or may be harmed by a narrative.
- Add framing and audience analysis without inferring sensitive traits.
- Add stakeholder-specific consequence and communication assessments.
- Integrate stakeholder maps with Catalyst Canvas.

**Release gate:** pressure-related findings are supported by explicit actor, incentive, relationship, and evidence records rather than an unexplained score.

### v1.8.0 — Comparative Narratives and Scenario Analysis

Enable structured comparison and stress testing.

- Compare competing claims, frames, source bases, assumptions, confidence levels, and review outcomes.
- Add side-by-side narrative dossiers and evidence matrices.
- Add counterfactual, best-case, base-case, worst-case, and adversarial review scenarios.
- Test sensitivity to scoring weights, source exclusions, new evidence, and altered consequence levels.
- Identify which assumptions or evidence items drive the largest change in disposition.
- Add narrative portfolios for campaigns, reports, decisions, institutions, and public issues.
- Add aggregate dashboards while preserving drill-down to individual records.
- Add Decision Studio scenario and decision-packet handoffs.

**Release gate:** comparative outputs remain transparent, reproducible, and traceable to the exact records and method versions used.

### v1.9.0 — Briefing, Publication, API, and Platform Integration

Make reviewed records usable across the Sustainable Catalyst platform.

- Add polished HTML, Markdown, PDF, JSON, CSV, JSON-LD, and review-bundle exports.
- Add public-safe briefs that omit private notes and protected source material.
- Add configurable report templates, branding, accessibility, print support, and citation sections.
- Add versioned REST endpoints, API keys, scopes, rate limits, idempotency, and OpenAPI documentation.
- Add embeddable read-only claim and review-status components.
- Add signed handoff contracts for Knowledge Library, Catalyst Data, Research Librarian, Site Intelligence, Catalyst Canvas, and Decision Studio.
- Add webhook/event support for record creation, review decisions, expiration, and material changes.
- Add WordPress administration, workspace, review, and public-display shortcodes.

**Release gate:** records can move between platform products without losing IDs, provenance, permissions, review state, or method reproducibility.

### v1.10.0 — Security, Privacy, Accessibility, and Production Hardening

Prepare the system for responsible institutional use.

- Add organization isolation, least-privilege permissions, secure sessions, CSRF protection, input sanitization, and output escaping.
- Add private evidence controls, field-level visibility, retention policies, deletion workflows, and export controls.
- Add security headers, dependency scanning, secret scanning, audit-log protection, and backup/restore validation.
- Add WCAG-oriented keyboard, screen-reader, contrast, focus, reduced-motion, and responsive testing.
- Add performance budgets, pagination, caching, background-job reliability, and graceful degradation.
- Add deployment health checks, migrations, rollback procedures, observability, and incident diagnostics.
- Add production release contracts for Python, JavaScript, PHP, schemas, APIs, migrations, and packaged artifacts.

**Release gate:** production readiness is demonstrated through repeatable security, accessibility, migration, backup, restore, and failure-recovery tests.

### v2.0.0 — Connected Narrative Risk and Claims Governance Platform

Deliver the complete institutional claims-governance system.

- Unified intake for claims, reports, messages, strategies, forecasts, and decision narratives.
- Structured claims, sources, evidence, assumptions, stakeholders, consequences, and intended-use records.
- Versioned transparent methods with reproducible scoring and visible human overrides.
- Persistent multi-user cases, review workflows, approvals, conditions, expirations, and audit history.
- Narrative maps, comparative analysis, temporal monitoring, drift detection, and reassessment.
- Organization-level policies, templates, permissions, dashboards, and governance reporting.
- First-party Sustainable Catalyst integrations and stable public APIs.
- Public-safe publication and private institutional workspaces.
- Accessible, secure, deployable, and portable release packages.

**v2.0 boundary:** the platform structures evidence and governance around narratives. It does not automatically certify truth, infer intent, approve communications, or replace legal, editorial, scientific, or domain judgment.

## Dependency sequence

1. Integrity and parity: v1.0.1.
2. Stable contracts and method versioning: v1.1.0.
3. Traceable evidence model: v1.2.0.
4. Persistence and workspaces: v1.3.0.
5. Complex claim modeling: v1.4.0.
6. Institutional review governance: v1.5.0.
7. Time-based monitoring: v1.6.0.
8. Stakeholder and pressure intelligence: v1.7.0.
9. Comparative and scenario analysis: v1.8.0.
10. Publication and integration: v1.9.0.
11. Production hardening: v1.10.0.
12. Connected platform release: v2.0.0.

## Immediate next build

**Build v1.0.1 — Scoring Parity and Release Integrity.**

This release should be completed before persistence, APIs, or new analytical features because the current WordPress JavaScript can produce different scores from the canonical Python engine. The v1.0.1 release should establish shared fixtures and release contracts that every later build inherits.
