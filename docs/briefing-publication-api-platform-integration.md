# Briefing, Publication, API, and Platform Integration

Catalyst Narrative Risk v1.9.0 turns an immutable analytical revision and its human-governance state into a controlled publication workflow.

## Publication objects

A **briefing** is an audience-specific representation of one immutable case revision. It includes the reviewed claim, risk interpretation, evidence coverage, narrative-map diagnostics, governance status, required wording, restrictions, disclosures, validity dates, reassessment dates, redaction metadata, the source record hash, and its own SHA-256 digest.

A **publication package** contains one or more checksummed artifacts. Supported formats are JSON, Markdown, HTML, PDF, CSV, and JSON-LD. Package status is `draft`, `ready`, `published`, `revoked`, or `superseded`. Idempotency keys prevent accidental duplicate package creation.

A **public embed** is a revocable configuration for a public-safe package. It records allowed origins, theme, visible sections, expiration, embed code, and an integrity digest.

A **platform handoff** carries a publication manifest—not untracked prose—to another Sustainable Catalyst product. The handoff includes the package hash and per-artifact hashes.

## Governance gate

Internal, confidential, and restricted briefings may be generated for review. A public briefing requires:

- an approved governance workflow;
- a current final disposition of `approve` or `approve_with_conditions`;
- completed required assignments;
- no blocking restriction such as `internal_only`, `embargoed`, or `no_public_claim`;
- no expired approval or due reassessment that disables publication.

Conditional restrictions and disclosures remain visible in the briefing and every downstream package.

## CLI example

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" create-briefing CASE_ID \
  --audience public --classification public --title "Reviewed Narrative Brief"
python python/narrative_risk_workspace.py --database "$DB" create-publication BRIEFING_ID \
  --format json --format markdown --format html --format pdf --format csv --format jsonld \
  --slug reviewed-narrative-brief --status ready --idempotency-key reviewed-brief-v1
python python/narrative_risk_workspace.py --database "$DB" publication-status PACKAGE_ID \
  --status published --public-url https://example.org/publications/reviewed-narrative-brief
python python/narrative_risk_workspace.py --database "$DB" create-embed PACKAGE_ID \
  --slug reviewed-narrative-brief-embed
python python/narrative_risk_workspace.py --database "$DB" platform-handoff PACKAGE_ID \
  --target knowledge_library
```

## Integrity

Artifact hashes are calculated over decoded bytes. Package, briefing, embed, and handoff hashes exclude their own digest field and cover every other field. Portable case bundles include all publication records and verify them during import.
