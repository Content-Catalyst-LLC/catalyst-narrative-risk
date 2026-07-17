# Migrating v1.7.0 Records to v1.8.0

The v1.8.0 migration validates the archived v1.7.0 schema, rebuilds the canonical record with the v1.8.0 method snapshot, and preserves the analytical score, risk level, evidence ledger, narrative map, identifiers, and human decision.

The migration does not fabricate comparison sets, competing frames, scenarios, sensitivity analyses, portfolios, or Decision Studio handoffs. These are workspace artifacts that require explicit records and assumptions.

```bash
python python/migrate_narrative_risk_record.py \
  --input v1.7.0-record.json \
  --output v1.8.0-record.json
```

Verify the result with:

```bash
python python/verify_narrative_risk_record.py --input v1.8.0-record.json
```
