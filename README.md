# Catalyst Narrative Risk

**Current release: v1.1.0 — Canonical Narrative Risk Contract and Method Engine**

Catalyst Narrative Risk is the Sustainable Catalyst platform layer for separating claims, evidence strength, uncertainty, volatility, pressure, consequences, machine interpretation, and accountable human decisions.

The module does not decide whether a claim is true. It creates a stable, reproducible review record that shows what entered the method, how every component was weighted, what the method inferred, and what a human reviewer ultimately decided.

## v1.1.0 contract

Every canonical record contains four distinct layers:

1. `normalized_input` — strict, controlled-vocabulary inputs with documented defaults.
2. `calculations` — component values, weights, rationale, remediation, totals, multiplier, score, and threshold.
3. `interpretation` — risk level, flags, actions, and the method's decision note.
4. `human_decision` — reviewer status and disposition, stored separately and never inferred from the score.

Each record also carries:

- Stable record and case identifiers
- Method, record-schema, and input-schema identifiers
- The complete versioned method snapshot
- SHA-256 method, input, and record-payload digests
- Exact record reproduction and verification support
- v1.0.1 migration metadata when applicable

## Canonical assets

```text
contracts/narrative-risk-contract.v1.1.0.json     Contract registry
contracts/controlled-vocabularies.v1.1.0.json    Controlled vocabularies and defaults
methods/transparent-heuristic.v1.1.0.json         Complete scoring and interpretation method
schemas/narrative_risk_input.schema.json          Canonical input schema
schemas/narrative_risk_method_snapshot.schema.json Method snapshot schema
schemas/narrative_risk_record.schema.json         Canonical record schema
schemas/archive/                                  Retained legacy schema for migration
```

## Python usage

```bash
python -m pip install -r requirements.txt

python python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out outputs/sample_narrative_risk_output.json \
  --markdown-out outputs/sample_narrative_risk_output.md
```

Verify an exported record:

```bash
python python/verify_narrative_risk_record.py \
  --input outputs/sample_narrative_risk_output.json
```

Migrate a v1.0.1 record:

```bash
python python/migrate_narrative_risk_record.py \
  --input tests/fixtures/legacy-v1.0.1-record.json \
  --output migrated-record.json
```

## API

- `POST /api/narrative-risk` — create a canonical record
- `POST /api/narrative-risk/verify` — validate and reproduce a record
- `POST /api/narrative-risk/migrate/v1.0.1` — migrate a legacy record
- `GET /api/narrative-risk/contract` — retrieve the contract registry
- `GET /api/narrative-risk/methods/current` — retrieve the current method snapshot and hash

## WordPress demo

Install `wordpress/catalyst-narrative-risk-demo/` and use:

```text
[catalyst_narrative_risk_demo]
```

The demo runs in the browser. It uses a generated method asset derived from the same canonical JSON method used by Python.

## Release validation

```bash
python -m pip install -r requirements-dev.txt
bash scripts/release_check.sh
```

The release suite covers Python tests, strict schemas, contract identity, method-asset synchronization, JavaScript and PHP syntax, browser fixtures, exact Python–JavaScript score and record parity, SHA-256 parity, CLI generation, migration, and reproducibility.

## Methodological boundary

Catalyst Narrative Risk structures evidence and review. It is not a fact-checking oracle, legal opinion, scientific certification, communications approval system, or automatic truth engine. Human judgment and domain expertise remain responsible for final decisions.
