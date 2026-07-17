# Narrative Change, Freshness, and Monitoring

Catalyst Narrative Risk v1.6.0 adds a monitoring layer around immutable analytical revisions and governed review records. Monitoring is advisory: it identifies change, aging evidence, and reassessment needs, but it does not alter the stored analytical score or grant, revoke, or renew approval automatically.

## Immutable monitoring snapshots

A snapshot captures the exact case revision, record digest, score, risk level, confidence state, claim wording, narrative nodes and links, source and evidence identifiers, source-freshness report, and current governance state. Each snapshot has its own SHA-256 digest and cannot be updated after creation.

Snapshots can be triggered manually, when a revision is created, by a schedule, by a Site Intelligence handoff, or during bundle import.

## Source freshness

Freshness is calculated from the most recent available access, import, evidence-capture, or publication date. The embedded method snapshot carries source-type-specific current, aging, and stale thresholds. Unknown dates remain explicitly unknown rather than being treated as current.

A stale source is a reassessment signal, not a claim that the source is false. The original source metadata and analytical record remain unchanged.

## Change comparison

Comparisons report:

- risk-score and risk-level change;
- added, removed, or modified claim wording;
- evidence-strength, uncertainty, and review-status change;
- added or removed sources and evidence;
- source-content digest and freshness change;
- narrative-node and link change;
- governance-status, publication, validity, and reassessment change.

A versioned materiality policy assigns an advisory score and severity to the detected differences. The comparison preserves the reasons contributing to the result.

## Watchlists and alerts

Watchlists define cadence, trigger types, optional source scope, status, next check, and ownership notes. Supported triggers include new evidence, material change, stale sources, source-content changes, score or wording changes, confidence changes, reassessment due, approval expiration, and Site Intelligence events.

Alerts are append-only records with open, acknowledged, and resolved states. Acknowledgement and resolution preserve the original alert and add explicit actor and time information.

## Timeline and bundles

The case timeline merges revisions, review events, governance decisions, monitoring snapshots, comparisons, alerts, and Site Intelligence events in chronological order.

Portable case bundles include all monitoring objects and protect them with the complete bundle SHA-256 digest. Import is transactional and exact export-import-re-export parity is part of the release gate.

## CLI examples

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" capture-snapshot CASE_ID
python python/narrative_risk_workspace.py --database "$DB" create-watch CASE_ID \
  --name "Daily narrative watch" --cadence daily \
  --trigger-type material_change --trigger-type source_stale
python python/narrative_risk_workspace.py --database "$DB" check-watch WATCH_ID
python python/narrative_risk_workspace.py --database "$DB" list-alerts --case-id CASE_ID
python python/narrative_risk_workspace.py --database "$DB" timeline CASE_ID
```
