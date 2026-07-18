# Security, Privacy, Accessibility, and Production Hardening

Catalyst Narrative Risk v2.0.0 adds an auditable hardening layer without changing the canonical analytical score.

## Security readiness

The security report evaluates the declared environment, debug mode, scoped API enforcement, administrator-token length, HTTPS, secure headers, CORS allowlists, request-size limits, persistent storage, backup configuration, retention policy, encryption-at-rest attestation, and secure cookies. Secret values are never copied into reports.

## Privacy and retention

Privacy policies define retention periods for case metadata, immutable revisions, review and governance records, monitoring, stakeholder, comparative, publication, API-usage, and activity records. Assessments calculate due dates and recommended actions. Legal holds block disposition recommendations.

## Backup and recovery

SQLite backups use the database backup API rather than a raw file copy. Each manifest records the database digest, table counts, schema version, integrity result, foreign-key status, size, and verification time. Restore is blocked unless verification succeeds.

## Accessibility

The WordPress audit checks semantic headings and landmarks, explicit form labels, typed buttons, visible keyboard focus, reduced-motion support, and accessible shortcode structures. Automated checks are a release gate, not a substitute for manual keyboard, screen-reader, zoom, contrast, and mobile testing.

## Performance

The default release budgets are 100 ms for health, 250 ms for listing 100 cases, 1,000 ms for exporting a case bundle, 5 MB per bundle, and 250 MB for the local SQLite database. Deployments may declare stricter budgets.

## Operator commands

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" database-diagnostics
python python/narrative_risk_workspace.py --database "$DB" create-privacy-policy --input privacy-policy.json
python python/narrative_risk_workspace.py --database "$DB" assess-retention CASE_ID
python python/narrative_risk_workspace.py --database "$DB" create-backup --output backups/narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" verify-backup BACKUP_ID
python python/narrative_risk_workspace.py --database "$DB" accessibility-audit
python python/narrative_risk_workspace.py --database "$DB" performance-audit --case-id CASE_ID
python python/narrative_risk_workspace.py --database "$DB" production-readiness --config production-config.json --case-id CASE_ID --backup-id BACKUP_ID
```
