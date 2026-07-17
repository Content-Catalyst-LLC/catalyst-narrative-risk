# Migration from v1.3.0

Catalyst Narrative Risk v1.4.0 accepts schema-valid v1.3.0 canonical records.

The migration:

- preserves the record ID, case ID, generated timestamp, analytical score, risk level, evidence ledger, and human decision
- embeds the v1.4.0 method and contract identifiers
- creates one deterministic narrative node for each existing ledger claim
- marks the primary ledger claim as the primary narrative node
- does not invent causal, predictive, dependency, or decomposition links
- records explicit migration warnings so reviewers know the generated map requires human decomposition

```bash
python python/migrate_narrative_risk_record.py \
  --input legacy-v1.3.0-record.json \
  --output migrated-v1.4.0-record.json
```

The resulting record is validated and exactly reproducible. Migration does not imply that a generated narrative map is review-ready.
