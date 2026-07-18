# Migrating v1.10.0 Records to v2.0.0

v2.0.0 accepts schema-valid v1.10.0 canonical records and preserves their identifiers, normalized input, evidence ledger, narrative map, score, risk level, interpretation, and human-decision layer.

Workspace governance, monitoring, stakeholder, comparative, publication, privacy, and hardening records remain separate workspace artifacts. v2.0.0 does not fabricate connected dossiers, platform events, integration routes, or institutional rollups during record migration.

```bash
python python/migrate_narrative_risk_record.py --input legacy-v1.10.0-record.json --output migrated-v2.0.0-record.json
python python/verify_narrative_risk_record.py --input migrated-v2.0.0-record.json
```
