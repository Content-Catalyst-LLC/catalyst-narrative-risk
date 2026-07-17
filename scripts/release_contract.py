#!/usr/bin/env python3
"""Validate the Catalyst Narrative Risk v1.1.0 release contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.contracts import (
    contract_definition,
    controlled_vocabularies,
    current_method_snapshot,
    load_json,
    sha256_digest,
)
from narrative_risk.migrations import migrate_v1_0_1_record
from narrative_risk.service import (
    CONTRACT_ID, INPUT_SCHEMA_ID, METHOD_ID, SCHEMA_ID, VERSION,
    validate_method_snapshot, validate_narrative_risk_record, verify_record_reproducibility,
)

REQUIRED_FILES = [
    "VERSION", "README.md", "CHANGELOG.md", "narrative_risk_manifest.json",
    "contracts/narrative-risk-contract.v1.1.0.json",
    "contracts/controlled-vocabularies.v1.1.0.json",
    "methods/transparent-heuristic.v1.1.0.json",
    "schemas/narrative_risk_input.schema.json",
    "schemas/narrative_risk_method_snapshot.schema.json",
    "schemas/narrative_risk_record.schema.json",
    "schemas/archive/narrative_risk_record.v1.0.1.schema.json",
    "narrative_risk/contracts.py", "narrative_risk/service.py", "narrative_risk/migrations.py",
    "python/narrative_risk_brief.py", "python/migrate_narrative_risk_record.py",
    "python/verify_narrative_risk_record.py",
    "tests/fixtures/scoring-parity.json", "tests/fixtures/legacy-v1.0.1-record.json",
    "scripts/generate_browser_method_asset.py", "scripts/cross_runtime_record_parity.py",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js",
    "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php",
    "release/v1.1.0.md",
]


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        fail("missing required release file(s): " + ", ".join(missing))

    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifest = load_json(ROOT / "narrative_risk_manifest.json")
    contract = contract_definition()
    vocabs = controlled_vocabularies()
    method = current_method_snapshot()
    input_schema = load_json(ROOT / "schemas/narrative_risk_input.schema.json")
    method_schema = load_json(ROOT / "schemas/narrative_risk_method_snapshot.schema.json")
    record_schema = load_json(ROOT / "schemas/narrative_risk_record.schema.json")
    fixtures = load_json(ROOT / "tests/fixtures/scoring-parity.json")
    sample = load_json(ROOT / "outputs/sample_narrative_risk_output.json")
    legacy = load_json(ROOT / "tests/fixtures/legacy-v1.0.1-record.json")
    plugin = (ROOT / "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php").read_text(encoding="utf-8")

    versions = {
        "VERSION": version_file,
        "Python VERSION": VERSION,
        "manifest version": manifest.get("version"),
        "manifest contract version": manifest.get("contract_version"),
        "manifest method version": manifest.get("method_version"),
        "manifest schema version": manifest.get("schema_version"),
        "contract version": contract.get("contract_version"),
        "method version": method.get("method_version"),
        "vocabulary version": vocabs.get("vocabulary_version"),
        "fixture contract": fixtures.get("contract_version"),
        "sample contract": sample.get("contract", {}).get("contract_version"),
        "sample method": sample.get("method_snapshot", {}).get("method_version"),
    }
    mismatches = {name: value for name, value in versions.items() if value != VERSION}
    if mismatches:
        fail(f"version mismatch: {mismatches}")

    identifiers = {
        "contract": contract.get("contract_id"),
        "Python contract": CONTRACT_ID,
        "manifest contract": manifest.get("contract_id"),
        "method": method.get("method_id"),
        "Python method": METHOD_ID,
        "manifest method": manifest.get("method_id"),
        "record schema": record_schema.get("$id"),
        "Python record schema": SCHEMA_ID,
        "manifest record schema": manifest.get("record_schema_id"),
        "input schema": input_schema.get("$id"),
        "Python input schema": INPUT_SCHEMA_ID,
        "manifest input schema": manifest.get("input_schema_id"),
    }
    expected = {
        "contract": CONTRACT_ID, "Python contract": CONTRACT_ID, "manifest contract": CONTRACT_ID,
        "method": METHOD_ID, "Python method": METHOD_ID, "manifest method": METHOD_ID,
        "record schema": SCHEMA_ID, "Python record schema": SCHEMA_ID, "manifest record schema": SCHEMA_ID,
        "input schema": INPUT_SCHEMA_ID, "Python input schema": INPUT_SCHEMA_ID, "manifest input schema": INPUT_SCHEMA_ID,
    }
    bad_ids = {name: value for name, value in identifiers.items() if value != expected[name]}
    if bad_ids:
        fail(f"identifier mismatch: {bad_ids}")

    if method_schema.get("$id") != contract.get("method_schema_id"):
        fail("method schema identifier mismatch")
    if contract.get("layers") != ["normalized_input", "calculations", "interpretation", "human_decision"]:
        fail("canonical layer order mismatch")
    if contract.get("compatibility", {}).get("migrates_from") != ["1.0.1"]:
        fail("v1.0.1 migration declaration missing")

    validate_method_snapshot(method)
    if sha256_digest(method) != sample.get("method_snapshot_sha256"):
        fail("sample method snapshot digest mismatch")
    validate_narrative_risk_record(sample)
    report = verify_record_reproducibility(sample)
    if not all(report[key] for key in ["exact_match", "method_snapshot_hash_match", "canonical_input_hash_match", "record_payload_hash_match"]):
        fail(f"sample reproducibility failed: {report}")

    migrated = migrate_v1_0_1_record(legacy, migrated_at="2026-07-17T14:00:00+00:00")
    if migrated["calculations"]["risk_score"] != legacy["risk_score"]:
        fail("migration did not preserve legacy score")
    if migrated["interpretation"]["risk_level"] != legacy["risk_level"]:
        fail("migration did not preserve legacy level")
    if not verify_record_reproducibility(migrated)["exact_match"]:
        fail("migrated record is not reproducible")

    source_vocab = vocabs["vocabularies"]["source_type"]
    if set(source_vocab["values"]) != set(method["weights"]["source_type"]):
        fail("source-type vocabulary and method weights differ")
    if set(method["algorithm"]["component_order"]) != set(method["components"]):
        fail("component order and method component metadata differ")
    for component in method["components"].values():
        if not component.get("rationale") or not component.get("remediation"):
            fail("component rationale or remediation missing")

    plugin_version = re.search(r"^ \* Version:\s*(\S+)", plugin, re.MULTILINE)
    if not plugin_version or plugin_version.group(1) != VERSION:
        fail("WordPress plugin header version mismatch")
    if "cnrisk-method-js" not in plugin or "array('cnrisk-method-js')" not in plugin:
        fail("WordPress method-to-engine dependency contract missing")
    if "array('cnrisk-engine-js')" not in plugin:
        fail("WordPress engine-to-interface dependency contract missing")

    if len(fixtures.get("valid", [])) < 6 or len(fixtures.get("invalid", [])) < 10:
        fail("parity fixture matrix is incomplete")

    for path in ROOT.rglob("*.json"):
        if any(part in {".git", ".venv"} for part in path.parts):
            continue
        json.loads(path.read_text(encoding="utf-8"))

    print("Catalyst Narrative Risk v1.1.0 release contract passed.")
    print(f"Version checks: {len(versions)}; identifier checks: {len(identifiers)}; parity fixtures: {len(fixtures['valid'])} valid, {len(fixtures['invalid'])} invalid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
