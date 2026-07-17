#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"

printf '\n==> Python tests\n'
"$PYTHON" -m pytest -q

printf '\n==> Python compile and canonical release contract\n'
"$PYTHON" -m compileall -q app narrative_risk python scripts tests
"$PYTHON" scripts/release_contract.py
"$PYTHON" scripts/generate_browser_method_asset.py --check

printf '\n==> Browser syntax, fixtures, ledger parity, and record parity\n'
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js
"$NODE" --check scripts/browser_record_dump.js
"$NODE" --check scripts/browser_fixture_dump.js
"$NODE" scripts/test_browser_engine.js
"$PYTHON" scripts/cross_runtime_parity.py
"$PYTHON" scripts/cross_runtime_record_parity.py

printf '\n==> CLI brief, bibliography, evidence-ledger exports, and exact reproduction\n'
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v120.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
"$PYTHON" python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out "$TMP_DIR/sample.json" \
  --markdown-out "$TMP_DIR/sample.md" \
  --bibliography-out "$TMP_DIR/source-list.md" \
  --generated-at 2026-07-17T12:00:00+00:00 \
  --record-id urn:uuid:30000000-0000-4000-8000-000000000001 \
  --case-id urn:uuid:30000000-0000-4000-8000-000000000002
"$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/sample.json"
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.json" --format json
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.md" --format markdown
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.csv" --format csv
for output in sample.md source-list.md ledger.json ledger.md ledger.csv; do test -s "$TMP_DIR/$output"; done
grep -q 'relationship_id,claim_id,claim_text' "$TMP_DIR/ledger.csv"

printf '\n==> Legacy migrations and post-migration reproduction\n'
for legacy in 1.0.1 1.1.0; do
  "$PYTHON" python/migrate_narrative_risk_record.py \
    --input "tests/fixtures/legacy-v${legacy}-record.json" \
    --output "$TMP_DIR/migrated-${legacy}.json" \
    --migrated-at 2026-07-17T14:00:00+00:00
  "$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/migrated-${legacy}.json"
done

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.2.0 release suite passed.\n'
