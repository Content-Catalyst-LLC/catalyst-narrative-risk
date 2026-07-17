# Catalyst Narrative Risk

**Current release: v1.3.0 — Persistent Cases and Review Workspaces**

Catalyst Narrative Risk is the Sustainable Catalyst platform layer for traceable claims, evidence, uncertainty, narrative interpretation, and accountable human review. v1.3.0 adds durable case management around the canonical analytical record.

The module does not certify whether a claim is true. It preserves what was claimed, which evidence was linked, how the transparent method calculated risk, what a reviewer decided, and how the case changed over time.

## v1.3.0 architecture

The release separates mutable workspace state from immutable analytical artifacts:

- **Cases** hold title, summary, organization and project references, status, priority, tags, archive state, and current revision pointers.
- **Revisions** hold complete canonical narrative-risk records and SHA-256 hashes. Revisions are never edited in place.
- **Review events** append comments, review requests, completed reviews, decision updates, status changes, and assignment changes.
- **Activity** is append-only and protected from update or deletion by SQLite triggers.
- **Saved views** preserve validated search and filtering criteria.
- **Portable bundles** contain a case, all revisions, review events, activity, and a complete bundle checksum.

The existing five canonical analytical layers remain unchanged:

1. `normalized_input`
2. `evidence_ledger`
3. `calculations`
4. `interpretation`
5. `human_decision`

## Canonical assets

```text
contracts/narrative-risk-contract.v1.3.0.json
contracts/controlled-vocabularies.v1.3.0.json
methods/transparent-heuristic.v1.3.0.json
schemas/narrative_risk_input.schema.json
schemas/narrative_risk_evidence_ledger.schema.json
schemas/narrative_risk_method_snapshot.schema.json
schemas/narrative_risk_record.schema.json
schemas/narrative_risk_case.schema.json
schemas/narrative_risk_revision.schema.json
schemas/narrative_risk_review_event.schema.json
schemas/narrative_risk_saved_view.schema.json
schemas/narrative_risk_workspace_bundle.schema.json
schemas/archive/
```

## Python analytical usage

```bash
python -m pip install -r requirements.txt

python python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out outputs/sample_narrative_risk_output.json \
  --markdown-out outputs/sample_narrative_risk_output.md \
  --bibliography-out outputs/sample_source_list.md
```

Verify a record:

```bash
python python/verify_narrative_risk_record.py \
  --input outputs/sample_narrative_risk_output.json
```

## Persistent workspace CLI

Initialize and create a persistent case:

```bash
python python/narrative_risk_workspace.py \
  --database data/catalyst-narrative-risk.sqlite3 init

python python/narrative_risk_workspace.py \
  --database data/catalyst-narrative-risk.sqlite3 create \
  --title "Pilot energy narrative" \
  --tag energy \
  --input data/sample_narrative_risk_input.json
```

The CLI also supports `list`, `show`, `add-revision`, `add-review`, `archive`, `restore`, `export`, `import`, `verify-bundle`, and `save-view`.

## REST API

Analytical endpoints:

- `POST /api/narrative-risk`
- `POST /api/narrative-risk/ledger/analyze`
- `POST /api/narrative-risk/verify`
- `POST /api/narrative-risk/migrate`
- `POST /api/narrative-risk/migrate/v1.0.1`
- `POST /api/narrative-risk/migrate/v1.1.0`
- `POST /api/narrative-risk/migrate/v1.2.0`
- `GET /api/narrative-risk/contract`
- `GET /api/narrative-risk/vocabularies`
- `GET /api/narrative-risk/methods/current`

Workspace endpoints:

- `GET /api/narrative-risk/workspaces/health`
- `POST|GET /api/narrative-risk/cases`
- `GET|PATCH /api/narrative-risk/cases/{case_id}`
- `POST /api/narrative-risk/cases/{case_id}/revisions`
- `POST /api/narrative-risk/cases/{case_id}/reviews`
- `POST /api/narrative-risk/cases/{case_id}/archive`
- `POST /api/narrative-risk/cases/{case_id}/restore`
- `GET /api/narrative-risk/cases/{case_id}/export`
- `POST /api/narrative-risk/cases/import`
- `POST|GET /api/narrative-risk/saved-views`

Set `CNRISK_DATABASE_PATH` to the persistent SQLite file. Flask otherwise uses `instance/catalyst-narrative-risk.sqlite3`.

## WordPress

Install `wordpress/catalyst-narrative-risk-demo/` and use:

```text
[catalyst_narrative_risk_demo]
[catalyst_narrative_risk_workspace]
```

The workspace shortcode provides browser-local case persistence and portable bundle import/export. The production persistence contract is the SQLite-backed REST API.

## Migration

The migration tool auto-detects v1.0.1, v1.1.0, and v1.2.0 records:

```bash
python python/migrate_narrative_risk_record.py \
  --input tests/fixtures/legacy-v1.2.0-record.json \
  --output migrated-v1.3.0-record.json
```

## Release validation

```bash
python -m pip install -r requirements-dev.txt
bash scripts/release_check.sh
```

The release gate covers Python tests, SQLite persistence, immutable revision hashes, append-only activity, bundle round trips, schemas, migrations, API and CLI behavior, browser parity, WordPress syntax, and packaged artifacts.

## Methodological boundary

Catalyst Narrative Risk structures evidence and review. It is not a fact-checking oracle, legal opinion, scientific certification, communications approval system, or automatic truth engine. Human judgment and domain expertise remain responsible for final decisions.
