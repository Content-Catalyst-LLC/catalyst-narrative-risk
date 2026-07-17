# Site Intelligence Monitoring Handoff

v1.6.0 defines a narrow, schema-validated handoff for Site Intelligence events that may affect a Narrative Risk case.

The handoff includes a stable event identifier, observation time, target case, event type, headline, summary, source URL and title, optional source-content digest, affected claim identifiers, confidence, and a product-specific payload.

Supported event types are `new_evidence`, `material_change`, `source_update`, and `narrative_shift`. Ingestion preserves the original handoff and its SHA-256 digest. Active watches configured for `site_intelligence_event` receive a monitoring alert. The event does not modify the narrative-risk record, evidence ledger, score, or governance decision automatically.

```bash
python python/narrative_risk_workspace.py \
  --database instance/catalyst-narrative-risk.sqlite3 \
  ingest-site-intelligence --input site-intelligence-event.json
```
