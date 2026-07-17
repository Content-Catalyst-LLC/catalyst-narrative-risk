#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"

printf '\n==> Python tests\n'
"$PYTHON" -m pytest -q

printf '\n==> Python compile and release contract\n'
"$PYTHON" -m compileall -q app narrative_risk python scripts tests
"$PYTHON" scripts/release_contract.py

printf '\n==> Browser engine syntax and fixture contract\n'
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js
"$NODE" --check wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js
"$NODE" scripts/test_browser_engine.js
"$PYTHON" scripts/cross_runtime_parity.py

printf '\n==> CLI export and schema validation\n'
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v101.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
"$PYTHON" python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out "$TMP_DIR/sample.json" \
  --markdown-out "$TMP_DIR/sample.md"
"$PYTHON" - "$TMP_DIR/sample.json" <<'PY'
import json
from pathlib import Path
import sys
from narrative_risk.service import validate_narrative_risk_record
record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
validate_narrative_risk_record(record)
assert Path(sys.argv[1]).with_suffix(".md").is_file()
print("CLI export schema validation passed.")
PY

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.0.1 release suite passed.\n'
