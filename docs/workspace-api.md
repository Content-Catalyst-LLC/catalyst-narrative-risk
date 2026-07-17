# Workspace REST API

The v1.3.0 API combines the canonical analytical engine with a persistent SQLite case repository.

Set `CNRISK_DATABASE_PATH` to the desired SQLite file. Without an override, Flask uses `instance/catalyst-narrative-risk.sqlite3`.

## Health

- `GET /healthz` returns analytical and workspace health.
- `GET /api/narrative-risk/workspaces/health` returns workspace version, database path, and table counts.

## Cases

- `POST /api/narrative-risk/cases` creates a case. An optional `initial_payload` creates revision 1.
- `GET /api/narrative-risk/cases` supports `query`, `organization_id`, `project_id`, `status`, `priority`, comma-separated `tags`, `archived`, `limit`, and `offset`.
- `GET /api/narrative-risk/cases/{case_id}` returns a case. `include_details=true` includes revisions, review events, and activity.
- `PATCH /api/narrative-risk/cases/{case_id}` changes mutable case metadata.
- `POST /api/narrative-risk/cases/{case_id}/archive` archives a case.
- `POST /api/narrative-risk/cases/{case_id}/restore` restores a case.

## Revisions and review activity

- `POST /api/narrative-risk/cases/{case_id}/revisions` accepts either `payload` or a complete canonical `record`.
- `POST /api/narrative-risk/cases/{case_id}/reviews` appends a review event.

A revision cannot be edited after creation. A new analytical state must be stored as the next revision.

## Portable bundles

- `GET /api/narrative-risk/cases/{case_id}/export` creates a checksummed case bundle.
- `POST /api/narrative-risk/cases/import` verifies and imports a bundle.

## Saved views

- `POST /api/narrative-risk/saved-views` stores a validated case filter.
- `GET /api/narrative-risk/saved-views` lists views, optionally filtered by `owner_id`.

## Errors

Validation failures return HTTP 400 with a stable error category and a human-readable message. The API does not silently coerce unsupported fields, invalid controlled vocabulary values, mismatched case identifiers, or damaged bundle hashes.
