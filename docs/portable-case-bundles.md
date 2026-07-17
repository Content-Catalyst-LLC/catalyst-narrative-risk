# Portable Case Bundles

A v1.4.0 case bundle is a self-contained JSON artifact with:

- Case metadata
- All immutable revisions and their canonical records
- Review events
- Append-only activity
- Export timestamp
- SHA-256 checksum of the complete unsigned bundle payload

The bundle type is `catalyst_narrative_risk_case_bundle` and the bundle version is `1.4.0`.

## Verification sequence

1. Validate the bundle against `schemas/narrative_risk_workspace_bundle.schema.json`.
2. Remove `bundle_sha256` and calculate the canonical SHA-256 digest.
3. Confirm the calculated digest equals the stored bundle digest.
4. Confirm every revision record digest equals `record_sha256`.
5. Confirm every revision belongs to the exported case.
6. Validate each embedded canonical narrative-risk record.
7. Import all entities in one database transaction.

A failed check aborts the complete import. Partial case imports are not committed.

## Portability guarantee

Exporting a case, importing it into an empty repository, and exporting it again with the same `exported_at` value produces an identical bundle. This preserves record identities, provenance, reviewer activity, revision order, and audit history.
