# Catalyst Narrative Risk

**Current release: v1.9.0 — Briefing, Publication, API, and Platform Integration**

Catalyst Narrative Risk is the Sustainable Catalyst layer for traceable claims, evidence, narrative structure, uncertainty, accountable review, monitoring, stakeholder intelligence, and comparative scenario analysis. It does not certify truth, infer intent, or select a preferred narrative automatically.

## What v1.9.0 adds

- Governance-aware internal, executive, technical, regulatory, media, and public briefings.
- Public-safety gates, required wording, restrictions, disclosures, redactions, validity, and reassessment metadata.
- Checksummed JSON, Markdown, HTML, PDF, CSV, and JSON-LD publication packages.
- Idempotent package creation, lifecycle status, public URLs, and artifact manifests.
- Revocable public embeds.
- Hashed and scoped API keys with expiry and per-minute rate limits.
- OpenAPI 3.1 discovery and publication endpoints.
- Checksummed handoffs to Sustainable Catalyst products and external systems.
- WordPress publication workspace and governed public-brief shortcode.

The v1.8.0 analytical, governance, monitoring, stakeholder, and comparative behavior remains unchanged. Publication approval is never inferred from the heuristic score.

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

The suite validates Python tests, schema contracts, exact reproduction, Python–JavaScript parity, the valid/invalid fixture matrix, all exports, workspace bundle transfer, all nine legacy migrations, JavaScript syntax, and WordPress PHP syntax.

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
