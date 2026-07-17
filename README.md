# Catalyst Narrative Risk

**Current release: v1.4.0 — Claim Decomposition and Narrative Mapping**

Catalyst Narrative Risk is the Sustainable Catalyst layer for traceable claims, evidence, narrative structure, uncertainty, interpretation, and accountable human review. It does not certify truth or infer intent. It makes the reasoning and review path inspectable.

## What v1.4.0 adds

- Atomic narrative nodes for factual, causal, predictive, normative, recommendation, assumption, context, and unknown statements
- Typed relationships such as decomposition, dependency, causation, prediction, support, qualification, contradiction, and context
- Explicit entities, geography, time scope, quantities, and baselines
- Wording variants with deterministic comparison metrics
- Advisory checks for ambiguity, overbreadth, unsupported causality, unbounded predictions, missing baselines, confidence mismatch, orphan nodes, unmapped claims, and dependency cycles
- A sixth canonical record layer: `narrative_map`
- Narrative-map SHA-256 integrity and exact Python–JavaScript reproduction
- JSON, Markdown, and Mermaid narrative-map exports
- v1.3.0 migration that preserves the analytical result and evidence ledger while creating deterministic map nodes from existing claims
- Updated REST and WordPress interfaces

The v1.3.0 persistent case, immutable revision, review history, saved-view, archive, and portable-bundle capabilities remain intact.

## Canonical six-layer record

1. `normalized_input`
2. `evidence_ledger`
3. `narrative_map`
4. `calculations`
5. `interpretation`
6. `human_decision`

The scoring algorithm is unchanged from v1.3.0. Narrative diagnostics are advisory and do not silently change the risk score.

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

The suite validates Python tests, schema contracts, exact reproduction, Python–JavaScript parity, the valid/invalid fixture matrix, all exports, workspace bundle transfer, all four legacy migrations, JavaScript syntax, and WordPress PHP syntax.

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

## WordPress shortcodes

```text
[catalyst_narrative_risk_demo]
[catalyst_narrative_risk_workspace]
```

Browser workspace storage is a local demonstration. Shared institutional persistence should use the SQLite-backed REST workspace API.

## Boundary

Catalyst Narrative Risk structures claims, evidence, assumptions, wording, and review decisions. It does not automatically determine truth, intent, legal sufficiency, scientific validity, or publication approval.
