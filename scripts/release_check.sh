#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v190.XXXXXX")"
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
  wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-publication.js \
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

printf '\n==> Persistent workspace, governance, monitoring, stakeholder, comparative, publication CLI, and portable bundle round trip\n'
SOURCE_DB="$TMP_DIR/source.sqlite3"; TARGET_DB="$TMP_DIR/target.sqlite3"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" init > "$TMP_DIR/workspace-health.json"
"$PYTHON" python/narrative_risk_workspace.py verify-bundle --input outputs/sample_case_bundle.json > "$TMP_DIR/sample-bundle-verification.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" import --input outputs/sample_case_bundle.json > "$TMP_DIR/imported-source.json"
read -r CASE_ID PACKAGE_ID EXPORTED_AT < <("$PYTHON" - <<'PYDATA'
import json
bundle=json.load(open('outputs/sample_case_bundle.json'))
print(bundle['case']['case_id'], bundle['publication_packages'][0]['package_id'], bundle['exported_at'])
assert len(bundle['publication_briefings']) == 1
assert len(bundle['publication_packages']) == 1
assert len(bundle['publication_packages'][0]['artifacts']) == 6
assert len(bundle['public_embeds']) == 1
assert len(bundle['platform_handoffs']) == 4
PYDATA
)
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" show "$CASE_ID" --details > "$TMP_DIR/case-details.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" list-briefings "$CASE_ID" > "$TMP_DIR/briefings.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" list-publications "$CASE_ID" --status published > "$TMP_DIR/publications.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" publication-artifact "$PACKAGE_ID" pdf --output "$TMP_DIR/release-public-briefing.pdf"
grep -a -q '^%PDF-1.4' "$TMP_DIR/release-public-briefing.pdf"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" create-api-key \
  --name "Release publisher" --scope publication:read --scope publication:write \
  --rate-limit-per-minute 10 --created-at 2026-07-17T20:40:00+00:00 --created-by release-suite > "$TMP_DIR/api-key.json"
API_KEY_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["api_key"]["api_key_id"])' "$TMP_DIR/api-key.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" list-api-keys > "$TMP_DIR/api-keys.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" revoke-api-key "$API_KEY_ID" > "$TMP_DIR/api-key-revoked.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" export "$CASE_ID" \
  --output "$TMP_DIR/source-reexport.json" --exported-at "$EXPORTED_AT"
cmp outputs/sample_case_bundle.json "$TMP_DIR/source-reexport.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" import --input "$TMP_DIR/source-reexport.json" > "$TMP_DIR/imported-target.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" export "$CASE_ID" \
  --output "$TMP_DIR/target-reexport.json" --exported-at "$EXPORTED_AT"
cmp "$TMP_DIR/source-reexport.json" "$TMP_DIR/target-reexport.json"

printf '\n==> Legacy migrations and post-migration reproduction\n'
"$PYTHON" - <<'PYDATA'
import json
from pathlib import Path
from narrative_risk.migrations import migrate_record
from narrative_risk.service import verify_record_reproducibility
for index, version in enumerate(("1.0.1","1.1.0","1.2.0","1.3.0","1.4.0","1.5.0","1.6.0","1.7.0","1.8.0"), start=1):
    source=json.loads(Path(f"tests/fixtures/legacy-v{version}-record.json").read_text())
    migrated=migrate_record(source,migrated_at=f"2026-07-17T{10+index:02d}:00:00+00:00")
    report=verify_record_reproducibility(migrated)
    assert report["exact_match"], (version,report)
print("Nine legacy migrations reproduced exactly.")
PYDATA
"$PYTHON" python/migrate_narrative_risk_record.py \
  --input tests/fixtures/legacy-v1.8.0-record.json \
  --output "$TMP_DIR/migrated-1.8.0.json" --migrated-at 2026-07-17T19:00:00+00:00
"$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/migrated-1.8.0.json"

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.9.0 release suite passed.\n'
