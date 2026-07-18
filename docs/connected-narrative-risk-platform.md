# Connected Narrative Risk and Claims Governance Platform

Catalyst Narrative Risk v2.0.0 unifies the project’s analytical, evidence, narrative-mapping, review-governance, monitoring, stakeholder, comparative, publication, and production-hardening capabilities behind one connected institutional contract.

## Connected module registry

The platform registers ten first-party modules:

- Narrative Risk
- Knowledge Library
- Catalyst Data
- Site Intelligence
- Catalyst Canvas
- Decision Studio
- Research Librarian
- Workbench
- Catalyst Analytics
- Publication API

A registered connection describes a governed route between modules. Registration does not grant permission to read protected records or bypass the source module’s access rules.

## Platform events

Platform events are persistent, idempotent records of material changes. Each event includes its source module, intended targets, case scope, event type, occurrence time, idempotency key, payload, and SHA-256 integrity value.

Submitting the same idempotency key and identical content returns the existing event. Submitting changed content under an existing key is rejected.

## Integration routes

An integration route records the source module, target module, artifact type, artifact identifier, delivery status, external reference, payload hash, and route hash. Routes coordinate artifacts; they do not copy authorization from one module to another.

## Connected case dossiers

A connected dossier summarizes one case across:

- analytical score, level, claims, sources, and narrative nodes;
- governance stage, disposition, publication control, and reassessment;
- monitoring alerts;
- stakeholder pressures and consequences;
- comparisons and evaluated scenarios;
- publication packages and handoffs;
- privacy and retention assessments;
- platform events and routes.

The dossier is derived from explicit stored records and carries its own integrity hash.

## Institutional workspaces

Institutional workspaces provide exact organization-scoped rollups. Cases enter a rollup only when their `organization_id` exactly matches the requested organization. The rollup reports case status, priorities, pending reviews, publication readiness, open alerts, connected dossiers, and per-module event and route counts.

## Interfaces

The connected platform is available through:

- SQLite persistence;
- REST endpoints;
- command-line operations;
- checksummed portable case bundles;
- the WordPress shortcode `[catalyst_narrative_risk_platform]`.

## Method boundary

Connected dossiers and institutional rollups summarize explicit records and routes. They do not alter risk scores, create approval, infer truth, or bypass source-module permissions.
