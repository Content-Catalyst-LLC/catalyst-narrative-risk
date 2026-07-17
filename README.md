# Catalyst Narrative Risk

**Current release: v1.5.0 — Review, Approval, and Governance Workflow**

Catalyst Narrative Risk is the Sustainable Catalyst layer for traceable claims, evidence, narrative structure, uncertainty, interpretation, and accountable human review. It does not certify truth or infer intent. It makes the reasoning, review, approval, and publication path inspectable.

## What v1.5.0 adds

- Versioned review templates with intake, domain, editorial, legal, compliance, and final stages
- Reviewer assignments, deadlines, acceptance, completion, waiver, escalation, and reviewer queues
- Role-based permissions embedded in the canonical method snapshot
- Append-only stage and final governance decisions
- Explicit approval conditions, required wording, publication restrictions, and disclosures
- Approval validity, expiration, mandatory reassessment, and publication-eligibility checks
- Governance workflow, assignment, decision, and template JSON Schemas
- Governance REST endpoints and command-line operations
- Browser-local WordPress governance workflow and portable governance bundles
- Deterministic migration from v1.4.0 without changing analytical results

The v1.4.0 claim decomposition, narrative mapping, evidence ledger, persistent cases, immutable revisions, review history, and bundle-transfer capabilities remain intact.

## Canonical analytical record

1. `normalized_input`
2. `evidence_ledger`
3. `narrative_map`
4. `calculations`
5. `interpretation`
6. `human_decision`

Governance is stored in the workspace around immutable revisions. The weighted score and narrative diagnostics remain advisory and cannot approve a claim automatically.

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

The suite validates Python tests, schema contracts, exact reproduction, Python–JavaScript parity, the valid/invalid fixture matrix, all exports, workspace bundle transfer, all five legacy migrations, JavaScript syntax, and WordPress PHP syntax.

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

## WordPress shortcodes

```text
[catalyst_narrative_risk_demo]
[catalyst_narrative_risk_workspace]
```

Browser workspace storage is a local demonstration. Shared institutional persistence should use the SQLite-backed REST workspace API.

## Boundary

Catalyst Narrative Risk structures claims, evidence, assumptions, wording, and review decisions. It does not automatically determine truth, intent, legal sufficiency, scientific validity, or publication approval.
