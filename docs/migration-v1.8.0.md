# Migrating v1.8.0 Records to v1.9.0

The migration preserves the immutable v1.8.0 analytical record: identifiers, normalized input, evidence ledger, narrative map, score, interpretation, and human-decision layer. It rebuilds the record with the v1.9.0 method snapshot and verifies that the score and risk level are unchanged.

Publication history is not fabricated. Briefings, packages, public embeds, scoped API keys, and platform handoffs begin only when explicitly created in v1.9.0.

```bash
python python/migrate_narrative_risk_record.py \
  --input legacy-v1.8.0-record.json \
  --output migrated-v1.9.0-record.json
python python/verify_narrative_risk_record.py --input migrated-v1.9.0-record.json
```
