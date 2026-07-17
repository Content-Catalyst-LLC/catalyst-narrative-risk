#!/usr/bin/env python3
"""Validate the Catalyst Narrative Risk v1.0.1 release contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import SCHEMA_VERSION, VERSION, validate_narrative_risk_record

REQUIRED_FILES = [
    "VERSION",
    "README.md",
    "CHANGELOG.md",
    "narrative_risk/service.py",
    "narrative_risk/legacy.py",
    "schemas/narrative_risk_record.schema.json",
    "tests/fixtures/scoring-parity.json",
    "scripts/release_check.sh",
    "scripts/test_browser_engine.js",
    "scripts/cross_runtime_parity.py",
    "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js",
    "release/v1.0.1.md",
]


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        fail("missing required release file(s): " + ", ".join(missing))

    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifest = json.loads((ROOT / "narrative_risk_manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/narrative_risk_record.schema.json").read_text(encoding="utf-8"))
    fixtures = json.loads((ROOT / "tests/fixtures/scoring-parity.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "outputs/sample_narrative_risk_output.json").read_text(encoding="utf-8"))
    plugin = (ROOT / "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php").read_text(encoding="utf-8")
    engine = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js").read_text(encoding="utf-8")

    versions = {
        "VERSION": version_file,
        "Python VERSION": VERSION,
        "Python schema version": SCHEMA_VERSION,
        "manifest version": manifest.get("version"),
        "manifest method version": manifest.get("method_version"),
        "manifest schema version": manifest.get("schema_version"),
        "fixture contract": fixtures.get("contract_version"),
        "schema method const": schema["properties"]["method_version"].get("const"),
        "schema schema const": schema["properties"]["schema_version"].get("const"),
        "sample method version": sample.get("method_version"),
        "sample schema version": sample.get("schema_version"),
    }
    mismatches = {name: value for name, value in versions.items() if value != "1.0.1"}
    if mismatches:
        fail(f"version mismatch: {mismatches}")

    plugin_version = re.search(r"^ \* Version:\s*(\S+)", plugin, re.MULTILINE)
    if not plugin_version or plugin_version.group(1) != VERSION:
        fail("WordPress plugin header version mismatch")
    if "'1.0.1'" not in plugin or "array('cnrisk-engine-js')" not in plugin:
        fail("WordPress asset version or engine dependency contract missing")

    forbidden_fallbacks = [
        "sourceWeights[input.source_type] ||",
        "evidenceWeights[input.evidence_strength] ||",
        "reviewWeights[input.review_status] ||",
    ]
    for pattern in forbidden_fallbacks:
        if pattern in engine:
            fail(f"truthy fallback can corrupt zero-weight values: {pattern}")

    if len(fixtures.get("valid", [])) < 6 or len(fixtures.get("invalid", [])) < 6:
        fail("parity fixture matrix is incomplete")

    validate_narrative_risk_record(sample)

    for path in ROOT.rglob("*.json"):
        if any(part in {".git", ".venv"} for part in path.parts):
            continue
        json.loads(path.read_text(encoding="utf-8"))

    print("Catalyst Narrative Risk v1.0.1 release contract passed.")
    print(f"Version checks: {len(versions) + 1}; parity fixtures: {len(fixtures['valid'])} valid, {len(fixtures['invalid'])} invalid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
