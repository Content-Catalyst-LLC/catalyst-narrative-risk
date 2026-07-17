#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v130.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
export CNRISK_DATABASE_PATH="$TMP_DIR/api-tests.sqlite3"

printf '\n==> Python tests (isolated workspace database)\n'
"$PYTHON" -m pytest -q

printf '\n==> Python compile and canonical release contract\n'
"$PYTHON" -m compileall -q app narrative_risk python scripts tests
"$PYTHON" scripts/release_contract.py
"$PYTHON" scripts/generate_browser_method_asset.py --check

printf '\n==> Browser syntax, fixtures, ledger parity, record parity, and workspace syntax\n'
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js
"$NODE" --check scripts/browser_record_dump.js
"$NODE" --check scripts/browser_fixture_dump.js
"$NODE" scripts/test_browser_engine.js
"$PYTHON" scripts/cross_runtime_parity.py
"$PYTHON" scripts/cross_runtime_record_parity.py

printf '\n==> CLI brief, bibliography, evidence-ledger exports, and exact reproduction\n'
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

printf '\n==> Persistent workspace CLI and portable bundle round trip\n'
SOURCE_DB="$TMP_DIR/source.sqlite3"
TARGET_DB="$TMP_DIR/target.sqlite3"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" init > "$TMP_DIR/workspace-health.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" create \
  --title "Release workspace case" --summary "Persistent release verification." \
  --status in_review --priority high --tag release --tag evidence \
  --input data/sample_narrative_risk_input.json --created-by release-suite > "$TMP_DIR/case.json"
CASE_ID="$($PYTHON -c 'import json,sys; print(json.load(open(sys.argv[1]))["case_id"])' "$TMP_DIR/case.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" show "$CASE_ID" --details > "$TMP_DIR/case-details.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" add-review "$CASE_ID" \
  --event-type comment --author-id release-suite --body "Release review event." > "$TMP_DIR/review.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" export "$CASE_ID" \
  --output "$TMP_DIR/case-bundle.json" --exported-at 2026-07-17T17:00:00+00:00
"$PYTHON" python/narrative_risk_workspace.py verify-bundle --input "$TMP_DIR/case-bundle.json" > "$TMP_DIR/bundle-verification.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" import --input "$TMP_DIR/case-bundle.json" > "$TMP_DIR/imported.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" show "$CASE_ID" --details > "$TMP_DIR/imported-details.json"
"$PYTHON" - "$TMP_DIR/bundle-verification.json" "$TMP_DIR/imported-details.json" <<'PY'
import json, sys
verification=json.load(open(sys.argv[1])); details=json.load(open(sys.argv[2]))
assert verification['bundle_sha256_match'] and verification['all_revision_hashes_match'] and verification['all_case_ids_match']
assert details['revision_count'] == 1 and details['review_event_count'] == 1
assert [item['event_type'] for item in details['activity']] == ['case_created','revision_added','review_event_added']
PY

printf '\n==> Legacy migrations and post-migration reproduction\n'
for legacy in 1.0.1 1.1.0 1.2.0; do
  "$PYTHON" python/migrate_narrative_risk_record.py \
    --input "tests/fixtures/legacy-v${legacy}-record.json" \
    --output "$TMP_DIR/migrated-${legacy}.json" \
    --migrated-at 2026-07-17T18:00:00+00:00
  "$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/migrated-${legacy}.json"
done

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.3.0 release suite passed.\n'
