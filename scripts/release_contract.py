#!/usr/bin/env python3
"""Validate the complete Catalyst Narrative Risk v1.2.0 release contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.contracts import (
    CATALYST_DATA_HANDOFF_SCHEMA_PATH,
    INPUT_SCHEMA_PATH,
    KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH,
    LEDGER_SCHEMA_PATH,
    METHOD_SCHEMA_PATH,
    RECORD_SCHEMA_PATH,
    contract_definition,
    controlled_vocabularies,
    current_method_snapshot,
    load_json,
    sha256_digest,
    validate_against_schema,
)
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.migrations import migrate_v1_0_1_record, migrate_v1_1_0_record
from narrative_risk.service import (
    CONTRACT_ID,
    INPUT_SCHEMA_ID,
    LEDGER_SCHEMA_ID,
    METHOD_ID,
    SCHEMA_ID,
    VERSION,
    validate_method_snapshot,
    validate_narrative_risk_record,
    verify_record_reproducibility,
)

REQUIRED_FILES = [
    "VERSION", "README.md", "CHANGELOG.md", "narrative_risk_manifest.json",
    "contracts/narrative-risk-contract.v1.2.0.json",
    "contracts/controlled-vocabularies.v1.2.0.json",
    "methods/transparent-heuristic.v1.2.0.json",
    "schemas/narrative_risk_input.schema.json",
    "schemas/narrative_risk_evidence_ledger.schema.json",
    "schemas/narrative_risk_method_snapshot.schema.json",
    "schemas/narrative_risk_record.schema.json",
    "schemas/knowledge_library_source_handoff.schema.json",
    "schemas/catalyst_data_source_handoff.schema.json",
    "schemas/archive/narrative_risk_record.v1.0.1.schema.json",
    "schemas/archive/narrative_risk_input.v1.1.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.1.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.1.0.schema.json",
    "narrative_risk/contracts.py", "narrative_risk/service.py", "narrative_risk/ledger.py",
    "narrative_risk/integrations.py", "narrative_risk/migrations.py",
    "python/narrative_risk_brief.py", "python/export_evidence_ledger.py",
    "python/migrate_narrative_risk_record.py", "python/verify_narrative_risk_record.py",
    "data/sample_narrative_risk_input.json",
    "data/handoffs/knowledge_library_source.json", "data/handoffs/catalyst_data_source.json",
    "outputs/sample_narrative_risk_output.json", "outputs/sample_narrative_risk_output.md",
    "outputs/sample_source_list.md", "outputs/sample_evidence_ledger.csv",
    "tests/fixtures/scoring-parity.json", "tests/fixtures/legacy-v1.0.1-record.json",
    "tests/fixtures/legacy-v1.1.0-record.json",
    "scripts/generate_browser_method_asset.py", "scripts/cross_runtime_record_parity.py",
    "scripts/cross_runtime_parity.py", "scripts/test_browser_engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js",
    "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php",
    "release/v1.2.0.md", "docs/claims-sources-evidence-ledger.md",
    "docs/provenance-and-citations.md", "docs/integration-handoffs.md", "docs/migration-v1.1.0.md",
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
    schemas = {
        "input": load_json(INPUT_SCHEMA_PATH),
        "ledger": load_json(LEDGER_SCHEMA_PATH),
        "method": load_json(METHOD_SCHEMA_PATH),
        "record": load_json(RECORD_SCHEMA_PATH),
        "knowledge_library": load_json(KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH),
        "catalyst_data": load_json(CATALYST_DATA_HANDOFF_SCHEMA_PATH),
    }
    fixtures = load_json(ROOT / "tests/fixtures/scoring-parity.json")
    sample_input = load_json(ROOT / "data/sample_narrative_risk_input.json")
    sample = load_json(ROOT / "outputs/sample_narrative_risk_output.json")
    legacy_v101 = load_json(ROOT / "tests/fixtures/legacy-v1.0.1-record.json")
    legacy_v110 = load_json(ROOT / "tests/fixtures/legacy-v1.1.0-record.json")
    knowledge_handoff = load_json(ROOT / "data/handoffs/knowledge_library_source.json")
    data_handoff = load_json(ROOT / "data/handoffs/catalyst_data_source.json")
    plugin_path = ROOT / "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php"
    plugin = plugin_path.read_text(encoding="utf-8")

    versions = {
        "VERSION": version_file,
        "Python VERSION": VERSION,
        "manifest version": manifest.get("version"),
        "manifest contract version": manifest.get("contract_version"),
        "manifest method version": manifest.get("method_version"),
        "manifest schema version": manifest.get("schema_version"),
        "manifest vocabulary version": manifest.get("controlled_vocabulary_version"),
        "contract version": contract.get("contract_version"),
        "method version": method.get("method_version"),
        "ledger policy version": method.get("ledger_policy", {}).get("policy_version"),
        "vocabulary version": vocabs.get("vocabulary_version"),
        "fixture contract": fixtures.get("contract_version"),
        "sample contract": sample.get("contract", {}).get("contract_version"),
        "sample method": sample.get("method_snapshot", {}).get("method_version"),
        "sample ledger": sample.get("evidence_ledger", {}).get("ledger_version"),
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
        "record schema": schemas["record"].get("$id"),
        "Python record schema": SCHEMA_ID,
        "manifest record schema": manifest.get("record_schema_id"),
        "input schema": schemas["input"].get("$id"),
        "Python input schema": INPUT_SCHEMA_ID,
        "manifest input schema": manifest.get("input_schema_id"),
        "ledger schema": schemas["ledger"].get("$id"),
        "Python ledger schema": LEDGER_SCHEMA_ID,
        "manifest ledger schema": manifest.get("ledger_schema_id"),
        "knowledge handoff schema": schemas["knowledge_library"].get("$id"),
        "manifest knowledge handoff": manifest.get("knowledge_library_handoff_schema_id"),
        "data handoff schema": schemas["catalyst_data"].get("$id"),
        "manifest data handoff": manifest.get("catalyst_data_handoff_schema_id"),
    }
    expected = {
        "contract": CONTRACT_ID, "Python contract": CONTRACT_ID, "manifest contract": CONTRACT_ID,
        "method": METHOD_ID, "Python method": METHOD_ID, "manifest method": METHOD_ID,
        "record schema": SCHEMA_ID, "Python record schema": SCHEMA_ID, "manifest record schema": SCHEMA_ID,
        "input schema": INPUT_SCHEMA_ID, "Python input schema": INPUT_SCHEMA_ID, "manifest input schema": INPUT_SCHEMA_ID,
        "ledger schema": LEDGER_SCHEMA_ID, "Python ledger schema": LEDGER_SCHEMA_ID, "manifest ledger schema": LEDGER_SCHEMA_ID,
        "knowledge handoff schema": contract["knowledge_library_handoff_schema_id"],
        "manifest knowledge handoff": contract["knowledge_library_handoff_schema_id"],
        "data handoff schema": contract["catalyst_data_handoff_schema_id"],
        "manifest data handoff": contract["catalyst_data_handoff_schema_id"],
    }
    bad_ids = {name: value for name, value in identifiers.items() if value != expected[name]}
    if bad_ids:
        fail(f"identifier mismatch: {bad_ids}")

    if schemas["method"].get("$id") != contract.get("method_schema_id"):
        fail("method schema identifier mismatch")
    if contract.get("layers") != ["normalized_input", "evidence_ledger", "calculations", "interpretation", "human_decision"]:
        fail("canonical layer order mismatch")
    if contract.get("compatibility", {}).get("migrates_from") != ["1.0.1", "1.1.0"]:
        fail("legacy migration declarations are incomplete")
    if manifest.get("migration_sources") != ["1.0.1", "1.1.0"]:
        fail("manifest migration sources are incomplete")

    validate_method_snapshot(method)
    validate_narrative_risk_record(sample)
    if sample["normalized_input"]["claim"] != sample_input["claim"]:
        fail("sample input and output primary claim differ")
    if sha256_digest(method) != sample.get("method_snapshot_sha256"):
        fail("sample method snapshot digest mismatch")
    if sha256_digest(sample["evidence_ledger"]) != sample["reproducibility"]["evidence_ledger_sha256"]:
        fail("sample evidence-ledger digest mismatch")
    report = verify_record_reproducibility(sample)
    required_checks = [
        "exact_match", "method_snapshot_hash_match", "canonical_input_hash_match",
        "evidence_ledger_hash_match", "record_payload_hash_match",
    ]
    if not all(report[key] for key in required_checks):
        fail(f"sample reproducibility failed: {report}")

    ledger = sample["evidence_ledger"]
    if not ledger["relationships"] or ledger["derived_scoring_inputs"]["ledger_applied"] is not True:
        fail("sample does not exercise ledger-derived scoring")
    if ledger["coverage"]["overall"]["source_count"] < 2:
        fail("sample does not exercise multiple sources")
    if len(ledger["source_list"]) != len(ledger["sources"]):
        fail("sample source-list coverage is incomplete")

    validate_against_schema(knowledge_handoff, KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH)
    validate_against_schema(data_handoff, CATALYST_DATA_HANDOFF_SCHEMA_PATH)
    if import_knowledge_library_source(knowledge_handoff)["provenance"]["acquisition_method"] != "knowledge_library":
        fail("Knowledge Library handoff provenance mismatch")
    if import_catalyst_data_source(data_handoff)["provenance"]["acquisition_method"] != "catalyst_data":
        fail("Catalyst Data handoff provenance mismatch")

    migrated_v101 = migrate_v1_0_1_record(legacy_v101, migrated_at="2026-07-17T14:00:00+00:00")
    migrated_v110 = migrate_v1_1_0_record(legacy_v110, migrated_at="2026-07-17T15:00:00+00:00")
    if migrated_v101["calculations"]["risk_score"] != legacy_v101["risk_score"]:
        fail("v1.0.1 migration did not preserve score")
    if migrated_v110["calculations"]["risk_score"] != legacy_v110["calculations"]["risk_score"]:
        fail("v1.1.0 migration did not preserve score")
    if migrated_v110["human_decision"] != legacy_v110["human_decision"]:
        fail("v1.1.0 migration did not preserve human decision")
    if not verify_record_reproducibility(migrated_v101)["exact_match"]:
        fail("v1.0.1 migrated record is not reproducible")
    if not verify_record_reproducibility(migrated_v110)["exact_match"]:
        fail("v1.1.0 migrated record is not reproducible")

    source_vocab = vocabs["vocabularies"]["source_type"]
    relation_vocab = vocabs["vocabularies"]["evidence_relation_type"]
    if set(source_vocab["values"]) != set(method["weights"]["source_type"]):
        fail("source-type vocabulary and method weights differ")
    if set(relation_vocab["values"]) != set(method["ledger_policy"]["counted_relation_types"]):
        fail("relationship vocabulary and method policy differ")
    if set(method["algorithm"]["component_order"]) != set(method["components"]):
        fail("component order and method metadata differ")
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
    demo_js = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js").read_text(encoding="utf-8")
    for token in ["evidence_ledger_json", "data-cnrisk-coverage", "data-cnrisk-sources", "v1.2.0.json"]:
        if token not in demo_js and token not in plugin:
            fail(f"WordPress evidence-ledger interface token missing: {token}")

    if len(fixtures.get("valid", [])) != 8 or len(fixtures.get("invalid", [])) != 23:
        fail("parity fixture matrix must contain exactly 8 valid and 23 invalid cases")

    for path in ROOT.rglob("*.json"):
        if any(part in {".git", ".venv", ".pytest_cache"} for part in path.parts):
            continue
        json.loads(path.read_text(encoding="utf-8"))

    for output in [
        ROOT / "outputs/sample_narrative_risk_output.md",
        ROOT / "outputs/sample_source_list.md",
        ROOT / "outputs/sample_evidence_ledger.csv",
    ]:
        if output.stat().st_size == 0:
            fail(f"empty sample output: {output.relative_to(ROOT)}")

    print("Catalyst Narrative Risk v1.2.0 release contract passed.")
    print(
        f"Version checks: {len(versions)}; identifier checks: {len(identifiers)}; "
        f"parity fixtures: {len(fixtures['valid'])} valid, {len(fixtures['invalid'])} invalid."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
