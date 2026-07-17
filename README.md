# Catalyst Narrative Risk

**Current release: v1.2.0 — Claims, Sources, and Evidence Ledger**

Catalyst Narrative Risk is the Sustainable Catalyst platform layer for traceable claims review. It connects narrative statements to structured sources, evidence excerpts, provenance, qualifications, contradictions, uncertainty, consequence, machine interpretation, and accountable human decisions.

The module does not certify whether a claim is true. It makes the review path inspectable: what was claimed, which evidence was linked, how source independence and contradictions affected the heuristic, what the method calculated, and what a human reviewer ultimately decided.

## v1.2.0 contract

Every canonical record contains five separate analytical and governance layers:

1. `normalized_input` — strict scalar inputs, including source values derived from the ledger when evidence relationships exist.
2. `evidence_ledger` — claims, sources, evidence excerpts, claim-evidence relationships, coverage, citations, provenance, and derived scoring inputs.
3. `calculations` — selected values, weights, rationale, remediation, totals, score, and threshold.
4. `interpretation` — risk level, flags, actions, and the method's decision note.
5. `human_decision` — reviewer status and disposition, stored separately and never inferred from the score.

Each record also carries stable record, case, method, input-schema, record-schema, and ledger-schema identifiers; the complete method snapshot; and SHA-256 digests for the method, normalized input, evidence ledger, and complete record payload.

## Evidence-ledger behavior

The ledger supports:

- Atomic primary, supporting, and contextual claims
- Structured source metadata, identifiers, independence groups, duplicate links, directness, freshness, and acquisition provenance
- Evidence excerpts with locators, capture timestamps, and excerpt hashes
- `support`, `qualify`, `contradict`, `contextualize`, and `unresolved` relationships
- Per-claim and overall coverage summaries
- Harvard-style citations and portable source lists
- Knowledge Library and Catalyst Data source handoffs

When the primary claim has evidence relationships, `source_type`, `evidence_strength`, and `source_count` are derived from the ledger. Conflicting manually supplied scalar values are rejected.

## Canonical assets

```text
contracts/narrative-risk-contract.v1.2.0.json
contracts/controlled-vocabularies.v1.2.0.json
methods/transparent-heuristic.v1.2.0.json
schemas/narrative_risk_input.schema.json
schemas/narrative_risk_evidence_ledger.schema.json
schemas/narrative_risk_method_snapshot.schema.json
schemas/narrative_risk_record.schema.json
schemas/knowledge_library_source_handoff.schema.json
schemas/catalyst_data_source_handoff.schema.json
schemas/archive/
```

## Python usage

```bash
python -m pip install -r requirements.txt

python python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out outputs/sample_narrative_risk_output.json \
  --markdown-out outputs/sample_narrative_risk_output.md \
  --bibliography-out outputs/sample_source_list.md
```

Export only the evidence ledger:

```bash
python python/export_evidence_ledger.py \
  --input outputs/sample_narrative_risk_output.json \
  --output outputs/sample_evidence_ledger.csv \
  --format csv
```

Verify an exported record:

```bash
python python/verify_narrative_risk_record.py \
  --input outputs/sample_narrative_risk_output.json
```

Migrate a v1.0.1 or v1.1.0 record:

```bash
python python/migrate_narrative_risk_record.py \
  --input tests/fixtures/legacy-v1.1.0-record.json \
  --output migrated-record.json
```

## API

- `POST /api/narrative-risk` — create a canonical v1.2.0 record
- `POST /api/narrative-risk/ledger/analyze` — analyze normalized inputs and the evidence ledger without assigning record IDs
- `POST /api/narrative-risk/verify` — validate and exactly reproduce a record
- `POST /api/narrative-risk/migrate` — auto-detect and migrate v1.0.1 or v1.1.0
- `POST /api/narrative-risk/migrate/v1.0.1`
- `POST /api/narrative-risk/migrate/v1.1.0`
- `POST /api/narrative-risk/import/knowledge-library`
- `POST /api/narrative-risk/import/catalyst-data`
- `GET /api/narrative-risk/contract`
- `GET /api/narrative-risk/vocabularies`
- `GET /api/narrative-risk/methods/current`

## WordPress demo

Install `wordpress/catalyst-narrative-risk-demo/` and use:

```text
[catalyst_narrative_risk_demo]
```

The browser demo accepts optional ledger JSON, derives source-related scoring inputs, displays evidence coverage and citations, and exports the same canonical record and SHA-256 digests as Python.

## Release validation

```bash
python -m pip install -r requirements-dev.txt
bash scripts/release_check.sh
```

The release gate covers Python tests, schemas, method generation, API and CLI behavior, migrations, handoffs, browser fixtures, exact Python–JavaScript ledger/record/digest parity, JSON/Markdown/CSV exports, JavaScript syntax, and PHP syntax.

## Methodological boundary

Catalyst Narrative Risk structures evidence and review. It is not a fact-checking oracle, legal opinion, scientific certification, communications approval system, or automatic truth engine. Human judgment and domain expertise remain responsible for final decisions.
