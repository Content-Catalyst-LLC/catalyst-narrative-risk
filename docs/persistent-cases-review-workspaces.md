# Persistent Cases and Review Workspaces

Catalyst Narrative Risk v1.4.0 adds a durable workspace layer around immutable canonical analytical records.

## Separation of responsibilities

A **case** is a mutable working envelope. It carries the title, summary, organization and project references, status, priority, tags, archive state, current revision number, and latest record identifier.

A **revision** is immutable. Each revision contains one complete canonical narrative-risk record, a revision number, a record digest, author context, timestamp, and change note. Existing revisions are never rewritten when a later assessment changes.

A **review event** is append-only activity such as a comment, review request, completed review, decision update, status change, or assignment change.

The **activity log** is also append-only. SQLite triggers prevent update and deletion of audit entries.

## Repository implementation

`narrative_risk.workspaces.SQLiteCaseRepository` provides:

- SQLite initialization and schema-version metadata
- Case creation, retrieval, update, search, archive, and restore
- Immutable numbered revisions
- Canonical record and revision hash verification
- Review events linked to an optional revision
- Saved views with validated filters
- Append-only case activity
- Portable checksummed case bundles
- Exact export and re-import into another repository

The repository uses Python's standard `sqlite3` module and does not add an ORM or database dependency. A persistent file path is appropriate for local or single-node deployment. The repository contract is intentionally isolated so a later PostgreSQL adapter can implement the same operations.

## Invariants

1. Every revision record must validate against the active canonical record schema.
2. A revision record's `case_id` must match its workspace case.
3. Record identifiers are globally unique within a repository.
4. Revision numbers are unique and monotonically increasing within a case.
5. The stored `record_sha256` must match the canonical record JSON.
6. Activity rows cannot be updated or deleted.
7. Import fails if a case identifier already exists.
8. Import fails if the bundle checksum, revision record checksum, or case relationship is invalid.

## Local and institutional interfaces

The Flask REST API is the durable institutional interface. The WordPress shortcode `[catalyst_narrative_risk_workspace]` provides a browser-local workspace for demonstration, private offline use, and interface testing. Browser mode uses local storage and clearly identifies that an institutional deployment should connect the interface to the REST workspace API.
