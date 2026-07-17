# Migrating v1.2.0 Records

Catalyst Narrative Risk v1.3.0 accepts schema-valid v1.2.0 canonical records.

The migration:

- Preserves the record ID and case ID
- Preserves the evidence ledger and all claim-evidence relationships
- Preserves the analytical score and risk level
- Preserves the human decision
- Rebuilds the record with the v1.3.0 contract and method snapshot
- Adds an explicit migration block

The migrated record is suitable for insertion as an immutable v1.3.0 case revision. Case title, status, priority, tags, review events, and saved views are workspace metadata and are not invented from the analytical record.

```bash
python python/migrate_narrative_risk_record.py \
  --input tests/fixtures/legacy-v1.2.0-record.json \
  --output migrated-v1.3.0-record.json
```
