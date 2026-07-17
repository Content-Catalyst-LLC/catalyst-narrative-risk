# Workspace API

The v1.4.0 Flask API combines the canonical analytical engine with SQLite-backed cases and revisions.

Analytical endpoints include health, score, record verification, evidence-ledger analysis, narrative-map analysis, and legacy migration through v1.3.0. Workspace endpoints create and search cases, add revisions and review events, update metadata, archive or restore cases, and transfer checksum-verified bundles.

`POST /api/narrative-risk/map/analyze` returns the normalized narrative map and advisory diagnostics without creating a persistent case.

Set `CNRISK_DATABASE_PATH` to an explicit file for deployment. Release validation always overrides it with a temporary database and never opens the live workspace.
