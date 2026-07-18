# Catalyst Narrative Risk

**Current release: v1.10.0 — Security, Privacy, Accessibility, and Production Hardening**

Catalyst Narrative Risk is the Sustainable Catalyst layer for traceable claims, evidence, narrative structure, uncertainty, accountable review, monitoring, stakeholder intelligence, and comparative scenario analysis. It does not certify truth, infer intent, or select a preferred narrative automatically.

## What v1.10.0 adds

- Secure Flask defaults, response headers, request-size limits, explicit CORS allowlists, and HTTPS enforcement options.
- Tamper-evident security-readiness and aggregate production-readiness reports.
- Versioned privacy and retention policies with case-level assessments and legal holds.
- Verified SQLite backups, checksummed manifests, integrity checks, and guarded restore drills.
- WordPress accessibility audits and a production-readiness shortcode.
- Performance budgets and database diagnostics.
- REST and CLI workflows for privacy, backup, accessibility, performance, and readiness.

The v1.9.0 analytical, governance, monitoring, stakeholder, comparative, and publication behavior remains unchanged. A readiness report documents explicit controls; it does not certify the deployment as secure.

## Repository layout

```text
contracts/                  Versioned contract and controlled vocabularies
methods/                    Versioned method snapshots
schemas/                    Active and archived JSON Schemas
narrative_risk/             Python engine, ledger, map, migrations, persistence
python/                     CLI tools
app/                        Flask REST API
wordpress/                  Browser-native demo and local workspace
outputs/                    Canonical sample artifacts
scripts/                    Release, parity, and asset-generation gates
tests/                      Python and cross-runtime fixtures
```

## Validate the release

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
PYTHON=.venv/bin/python bash scripts/release_check.sh
```

The suite validates Python tests, schema contracts, exact reproduction, Python–JavaScript parity, the valid/invalid fixture matrix, all exports, workspace bundle transfer, all ten legacy migrations, JavaScript syntax, and WordPress PHP syntax.

## Generate a canonical record

```bash
python python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out record.json \
  --markdown-out brief.md \
  --bibliography-out sources.md
```

## Export the narrative map

```bash
python python/export_narrative_map.py --input record.json --output map.json --format json
python python/export_narrative_map.py --input record.json --output map.md --format markdown
python python/export_narrative_map.py --input record.json --output map.mmd --format mermaid
```

## Verify exact reproduction

```bash
python python/verify_narrative_risk_record.py --input record.json
```

## Persistent workspace

```bash
python python/narrative_risk_workspace.py --database instance/catalyst-narrative-risk.sqlite3 init
python python/narrative_risk_workspace.py --database instance/catalyst-narrative-risk.sqlite3 create \
  --title "Narrative review" --input data/sample_narrative_risk_input.json
```


## Governed review workflow

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" start-governance CASE_ID
python python/narrative_risk_workspace.py --database "$DB" assign-review WORKFLOW_ID   --stage domain --reviewer-id reviewer@example.org --reviewer-role domain_reviewer
python python/narrative_risk_workspace.py --database "$DB" decide WORKFLOW_ID   --stage domain --disposition approve --assignment-id ASSIGNMENT_ID   --decided-by reviewer@example.org --decider-role domain_reviewer   --rationale "Evidence and qualifications are suitable for the stated use."
```

See `docs/review-approval-governance-workflow.md` for the complete governance contract.

## Monitoring workflow

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

See `docs/narrative-change-freshness-monitoring.md` and `docs/site-intelligence-monitoring-handoff.md`.

## WordPress shortcodes

```text
[catalyst_narrative_risk_demo]
[catalyst_narrative_risk_workspace]
[catalyst_narrative_risk_publication_workspace]
[catalyst_narrative_risk_public_brief]
[catalyst_narrative_risk_readiness]
```

Browser workspace storage is a local demonstration. Shared institutional persistence should use the SQLite-backed REST workspace API.

## Boundary

Catalyst Narrative Risk structures claims, evidence, assumptions, wording, and review decisions. It does not automatically determine truth, intent, legal sufficiency, scientific validity, or publication approval.

## Stakeholder intelligence workflow

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" add-stakeholder-actor CASE_ID --input actor.json
python python/narrative_risk_workspace.py --database "$DB" add-stakeholder-pressure CASE_ID --input pressure.json
python python/narrative_risk_workspace.py --database "$DB" stakeholder-intelligence CASE_ID
python python/narrative_risk_workspace.py --database "$DB" import-catalyst-canvas CASE_ID --input data/handoffs/catalyst_canvas_stakeholder_handoff.json
```

See `docs/stakeholder-incentive-pressure-intelligence.md` and `docs/catalyst-canvas-stakeholder-handoff.md`.


## Comparative workflow

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" create-comparison CASE_ID --input comparison.json
python python/narrative_risk_workspace.py --database "$DB" evidence-matrix COMPARISON_ID
python python/narrative_risk_workspace.py --database "$DB" create-scenario COMPARISON_ID --input scenario.json
python python/narrative_risk_workspace.py --database "$DB" evaluate-scenario SCENARIO_ID
python python/narrative_risk_workspace.py --database "$DB" sensitivity COMPARISON_ID --dimension uncertainty --dimension consequences
python python/narrative_risk_workspace.py --database "$DB" comparative-portfolio CASE_ID
python python/narrative_risk_workspace.py --database "$DB" decision-studio-handoff COMPARISON_ID
```

See `docs/comparative-narratives-scenario-analysis.md` and `docs/decision-studio-handoff.md`.

## Publication workflow

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" create-briefing CASE_ID --audience public --classification public
python python/narrative_risk_workspace.py --database "$DB" create-publication BRIEFING_ID --format json --format markdown --format html --format pdf --format csv --format jsonld --slug reviewed-narrative --status ready
python python/narrative_risk_workspace.py --database "$DB" publication-status PACKAGE_ID --status published --public-url https://example.org/reviewed-narrative
python python/narrative_risk_workspace.py --database "$DB" create-embed PACKAGE_ID
python python/narrative_risk_workspace.py --database "$DB" platform-handoff PACKAGE_ID --target knowledge_library
```

See `docs/briefing-publication-api-platform-integration.md`, `docs/openapi.md`, and `docs/wordpress-publication.md`.


## Production hardening workflow

```bash
DB=instance/catalyst-narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" database-diagnostics
python python/narrative_risk_workspace.py --database "$DB" create-privacy-policy --input privacy-policy.json
python python/narrative_risk_workspace.py --database "$DB" assess-retention CASE_ID
python python/narrative_risk_workspace.py --database "$DB" create-backup --output backups/narrative-risk.sqlite3
python python/narrative_risk_workspace.py --database "$DB" verify-backup BACKUP_ID
python python/narrative_risk_workspace.py --database "$DB" production-readiness --config production-config.json --case-id CASE_ID --backup-id BACKUP_ID
```

See `docs/security-privacy-accessibility-production-hardening.md` and `docs/migration-v1.9.0.md`.
