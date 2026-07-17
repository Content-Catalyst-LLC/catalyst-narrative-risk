# Migrating v1.5.0 Records to v1.6.0

The v1.6.0 migration accepts a schema-valid v1.5.0 record and preserves its normalized input, evidence ledger, narrative map, calculations, interpretation, human decision, score, and risk level.

The record is rebuilt under the v1.6.0 contract and method snapshot, with deterministic migration metadata and exact reproducibility verification. The migration does not fabricate historical snapshots, watchlists, alerts, Site Intelligence events, or reassessment activity. Monitoring starts only when the migrated record is stored as a case revision and a snapshot or watch is created explicitly.

```bash
python python/migrate_narrative_risk_record.py \
  --input legacy-v1.5.0-record.json \
  --output migrated-v1.6.0-record.json
```
