# Migrating v1.4.0 Records to v1.5.0

The v1.5.0 migration upgrades a schema-valid v1.4.0 analytical record without changing its risk score, risk level, evidence ledger, narrative map, or human-decision layer.

The migrated record receives:

- v1.5.0 contract, schema, method, ledger, and narrative-map versions;
- the v1.5.0 governance policy inside the embedded method snapshot;
- recalculated method, input, ledger, map, and record-payload hashes;
- explicit migration metadata identifying v1.4.0 as the source;
- an exact reproducibility report under the v1.5.0 contract.

Migration does not create a governance workflow, assign reviewers, or infer approval from `review_status` or the prior human-decision field. Governance begins only when an authorized user starts a workflow against an immutable case revision.

Command:

```bash
python python/migrate_narrative_risk_record.py \
  --input legacy-v1.4.0-record.json \
  --output migrated-v1.5.0-record.json
```
