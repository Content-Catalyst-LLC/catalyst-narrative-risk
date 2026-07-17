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

printf '\n==> Browser engine syntax, fixtures, and runtime parity\n'
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js
"$NODE" --check scripts/browser_record_dump.js
"$NODE" scripts/test_browser_engine.js
"$PYTHON" scripts/cross_runtime_parity.py
"$PYTHON" scripts/cross_runtime_record_parity.py

printf '\n==> CLI export, schema, and exact reproduction\n'
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v110.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
"$PYTHON" python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out "$TMP_DIR/sample.json" \
  --markdown-out "$TMP_DIR/sample.md" \
  --generated-at 2026-07-17T12:00:00+00:00 \
  --record-id urn:uuid:30000000-0000-4000-8000-000000000001 \
  --case-id urn:uuid:30000000-0000-4000-8000-000000000002
"$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/sample.json"
test -s "$TMP_DIR/sample.md"

printf '\n==> v1.0.1 migration and post-migration reproduction\n'
"$PYTHON" python/migrate_narrative_risk_record.py \
  --input tests/fixtures/legacy-v1.0.1-record.json \
  --output "$TMP_DIR/migrated.json" \
  --migrated-at 2026-07-17T14:00:00+00:00
"$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/migrated.json"

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.1.0 release suite passed.\n'
