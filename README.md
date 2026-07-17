# Catalyst Narrative Risk

**Current release: v1.6.0 — Narrative Change, Freshness, and Monitoring**

Catalyst Narrative Risk is the Sustainable Catalyst layer for traceable claims, evidence, narrative structure, uncertainty, interpretation, and accountable human review. It does not certify truth or infer intent. It makes the reasoning, review, approval, and publication path inspectable.

## What v1.6.0 adds

- Immutable monitoring snapshots for analytical revisions and governance state.
- Versioned source-freshness policies with current, aging, stale, and unknown states.
- Claim wording, evidence, narrative-map, score, confidence, and governance comparisons.
- Advisory materiality scoring with explicit reasons and severity.
- Persistent watchlists, monitoring checks, alerts, acknowledgement, and resolution.
- Approval-expiration and reassessment-due monitoring signals.
- Site Intelligence monitoring handoffs without automatic record mutation.
- Unified case timelines and monitoring-complete portable bundles.

The v1.5.0 analytical and governance boundaries remain intact. Monitoring never verifies truth, changes an analytical score silently, or grants approval automatically.

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

The suite validates Python tests, schema contracts, exact reproduction, Python–JavaScript parity, the valid/invalid fixture matrix, all exports, workspace bundle transfer, all six legacy migrations, JavaScript syntax, and WordPress PHP syntax.

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
```

Browser workspace storage is a local demonstration. Shared institutional persistence should use the SQLite-backed REST workspace API.

## Boundary

Catalyst Narrative Risk structures claims, evidence, assumptions, wording, and review decisions. It does not automatically determine truth, intent, legal sufficiency, scientific validity, or publication approval.
