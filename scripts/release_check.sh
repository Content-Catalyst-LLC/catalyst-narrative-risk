#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v1100.XXXXXX")"
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

printf '\n==> Production hardening smoke checks\n'
"$PYTHON" python/narrative_risk_workspace.py --database "$TMP_DIR/hardening.sqlite3" init > "$TMP_DIR/hardening-health.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TMP_DIR/hardening.sqlite3" database-diagnostics > "$TMP_DIR/database-diagnostics.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TMP_DIR/hardening.sqlite3" accessibility-audit --plugin-root wordpress/catalyst-narrative-risk-demo --generated-at 2026-07-17T20:42:00+00:00 > "$TMP_DIR/accessibility.json"
"$PYTHON" - "$TMP_DIR/accessibility.json" "$TMP_DIR/database-diagnostics.json" <<'PYDATA'
import json, sys
assert json.load(open(sys.argv[1]))["status"] == "pass"
assert json.load(open(sys.argv[2]))["integrity_check"] == "ok"
PYDATA

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.10.0 release suite passed.\n'
