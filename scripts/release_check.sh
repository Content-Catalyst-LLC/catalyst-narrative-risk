#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v140.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
export CNRISK_DATABASE_PATH="$TMP_DIR/api-tests.sqlite3"

printf '\n==> Python tests (isolated workspace database)\n'
"$PYTHON" -m pytest -q

printf '\n==> Python compile and canonical release contract\n'
"$PYTHON" -m compileall -q app narrative_risk python scripts tests
"$PYTHON" scripts/release_contract.py
"$PYTHON" scripts/generate_browser_method_asset.py --check

printf '\n==> Browser syntax, fixture matrix, map parity, record parity, and workspace syntax\n'
for file in \
  wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js \
  wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-map.js \
  wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js \
  wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js \
  wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js \
  scripts/browser_record_dump.js scripts/browser_fixture_dump.js; do
  "$NODE" --check "$file"
done
"$NODE" scripts/test_browser_engine.js
"$PYTHON" scripts/cross_runtime_parity.py
"$PYTHON" scripts/cross_runtime_record_parity.py

printf '\n==> CLI brief, ledger exports, map exports, and exact reproduction\n'
"$PYTHON" python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out "$TMP_DIR/sample.json" --markdown-out "$TMP_DIR/sample.md" \
  --bibliography-out "$TMP_DIR/source-list.md" \
  --generated-at 2026-07-17T12:00:00+00:00 \
  --record-id urn:uuid:30000000-0000-4000-8000-000000000001 \
  --case-id urn:uuid:30000000-0000-4000-8000-000000000002
"$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/sample.json"
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.json" --format json
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.md" --format markdown
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.csv" --format csv
"$PYTHON" python/export_narrative_map.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/map.json" --format json
"$PYTHON" python/export_narrative_map.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/map.md" --format markdown
"$PYTHON" python/export_narrative_map.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/map.mmd" --format mermaid
for output in sample.md source-list.md ledger.json ledger.md ledger.csv map.json map.md map.mmd; do test -s "$TMP_DIR/$output"; done
grep -q 'relationship_id,claim_id,claim_text' "$TMP_DIR/ledger.csv"
grep -q 'flowchart TD' "$TMP_DIR/map.mmd"
grep -q 'Narrative Map' "$TMP_DIR/map.md"

printf '\n==> Persistent workspace CLI and portable bundle round trip\n'
SOURCE_DB="$TMP_DIR/source.sqlite3"; TARGET_DB="$TMP_DIR/target.sqlite3"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" init > "$TMP_DIR/workspace-health.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" create \
  --title "Release narrative-map case" --summary "Persistent v1.4.0 release verification." \
  --status in_review --priority high --tag release --tag narrative-map \
  --input data/sample_narrative_risk_input.json --created-by release-suite > "$TMP_DIR/case.json"
CASE_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["case_id"])' "$TMP_DIR/case.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" show "$CASE_ID" --details > "$TMP_DIR/case-details.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" add-review "$CASE_ID" \
  --event-type comment --author-id release-suite --body "Narrative-map release review event." > "$TMP_DIR/review.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" export "$CASE_ID" \
  --output "$TMP_DIR/case-bundle.json" --exported-at 2026-07-17T17:00:00+00:00
"$PYTHON" python/narrative_risk_workspace.py verify-bundle --input "$TMP_DIR/case-bundle.json" > "$TMP_DIR/bundle-verification.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" import --input "$TMP_DIR/case-bundle.json" > "$TMP_DIR/imported.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" export "$CASE_ID" \
  --output "$TMP_DIR/reexported.json" --exported-at 2026-07-17T17:00:00+00:00
cmp "$TMP_DIR/case-bundle.json" "$TMP_DIR/reexported.json"

printf '\n==> Legacy migrations and post-migration reproduction\n'
for legacy in 1.0.1 1.1.0 1.2.0 1.3.0; do
  "$PYTHON" python/migrate_narrative_risk_record.py \
    --input "tests/fixtures/legacy-v${legacy}-record.json" \
    --output "$TMP_DIR/migrated-${legacy}.json" --migrated-at 2026-07-17T18:00:00+00:00
  "$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/migrated-${legacy}.json"
done

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.4.0 release suite passed.\n'
