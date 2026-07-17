# Workspace API

The v1.6.0 Flask API combines the canonical analytical engine with SQLite-backed cases, immutable revisions, review history, and governed approvals.

Analytical endpoints include health, score, record verification, evidence-ledger analysis, narrative-map analysis, and legacy migration through v1.4.0.

Workspace endpoints create and search cases, add revisions and review events, update metadata, archive or restore cases, save views, and transfer checksum-verified bundles.

Governance endpoints provide:

- review-template creation and listing;
- workflow creation and retrieval;
- reviewer assignment and assignment status changes;
- reviewer queues and reassessment-due lists;
- append-only stage and final decisions;
- conditional approval and publication controls.

`POST /api/narrative-risk/map/analyze` returns the normalized narrative map and advisory diagnostics without creating a persistent case.

Set `CNRISK_DATABASE_PATH` to an explicit file for deployment. Release validation always overrides it with a temporary database and never opens the live workspace.

## Monitoring endpoints

- `POST/GET /api/narrative-risk/cases/{case_id}/monitoring/snapshots`
- `POST /api/narrative-risk/monitoring/compare`
- `POST/GET /api/narrative-risk/cases/{case_id}/watchlists`
- `PATCH /api/narrative-risk/watchlists/{watch_id}`
- `POST /api/narrative-risk/watchlists/{watch_id}/check`
- `GET /api/narrative-risk/monitoring/alerts`
- `PATCH /api/narrative-risk/monitoring/alerts/{alert_id}`
- `GET /api/narrative-risk/cases/{case_id}/timeline`
- `POST /api/narrative-risk/monitoring/site-intelligence`

Monitoring responses remain advisory and never mutate analytical scores or governance approvals implicitly.
