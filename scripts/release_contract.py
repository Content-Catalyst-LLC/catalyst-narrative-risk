#!/usr/bin/env python3
"""Validate the complete Catalyst Narrative Risk v1.3.0 release contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.contracts import (
    CATALYST_DATA_HANDOFF_SCHEMA_PATH,
    CASE_SCHEMA_PATH,
    INPUT_SCHEMA_PATH,
    KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH,
    LEDGER_SCHEMA_PATH,
    METHOD_SCHEMA_PATH,
    RECORD_SCHEMA_PATH,
    REVIEW_EVENT_SCHEMA_PATH,
    REVISION_SCHEMA_PATH,
    SAVED_VIEW_SCHEMA_PATH,
    WORKSPACE_BUNDLE_SCHEMA_PATH,
    contract_definition,
    controlled_vocabularies,
    current_method_snapshot,
    load_json,
    sha256_digest,
    validate_against_schema,
)
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.migrations import migrate_v1_0_1_record, migrate_v1_1_0_record, migrate_v1_2_0_record
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
from narrative_risk.workspaces import SQLiteCaseRepository

REQUIRED_FILES = [
    "VERSION", "README.md", "CHANGELOG.md", "narrative_risk_manifest.json",
    "contracts/narrative-risk-contract.v1.3.0.json",
    "contracts/controlled-vocabularies.v1.3.0.json",
    "methods/transparent-heuristic.v1.3.0.json",
    "schemas/narrative_risk_input.schema.json",
    "schemas/narrative_risk_evidence_ledger.schema.json",
    "schemas/narrative_risk_method_snapshot.schema.json",
    "schemas/narrative_risk_record.schema.json",
    "schemas/narrative_risk_case.schema.json",
    "schemas/narrative_risk_revision.schema.json",
    "schemas/narrative_risk_review_event.schema.json",
    "schemas/narrative_risk_saved_view.schema.json",
    "schemas/narrative_risk_workspace_bundle.schema.json",
    "schemas/knowledge_library_source_handoff.schema.json",
    "schemas/catalyst_data_source_handoff.schema.json",
    "schemas/archive/narrative_risk_record.v1.2.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.2.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.2.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.2.0.schema.json",
    "narrative_risk/contracts.py", "narrative_risk/service.py", "narrative_risk/ledger.py",
    "narrative_risk/integrations.py", "narrative_risk/migrations.py", "narrative_risk/workspaces.py",
    "python/narrative_risk_brief.py", "python/export_evidence_ledger.py",
    "python/migrate_narrative_risk_record.py", "python/verify_narrative_risk_record.py",
    "python/narrative_risk_workspace.py",
    "data/sample_narrative_risk_input.json",
    "outputs/sample_narrative_risk_output.json", "outputs/sample_narrative_risk_output.md",
    "outputs/sample_source_list.md", "outputs/sample_evidence_ledger.csv", "outputs/sample_case_bundle.json",
    "tests/fixtures/scoring-parity.json", "tests/fixtures/legacy-v1.0.1-record.json",
    "tests/fixtures/legacy-v1.1.0-record.json", "tests/fixtures/legacy-v1.2.0-record.json",
    "tests/test_workspaces.py",
    "scripts/generate_browser_method_asset.py", "scripts/cross_runtime_record_parity.py",
    "scripts/cross_runtime_parity.py", "scripts/test_browser_engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.css",
    "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php",
    "release/v1.3.0.md", "docs/persistent-cases-review-workspaces.md",
    "docs/workspace-api.md", "docs/portable-case-bundles.md", "docs/migration-v1.2.0.md",
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
    previous_method = load_json(ROOT / "methods/transparent-heuristic.v1.2.0.json")
    schemas = {
        "input": load_json(INPUT_SCHEMA_PATH), "ledger": load_json(LEDGER_SCHEMA_PATH),
        "method": load_json(METHOD_SCHEMA_PATH), "record": load_json(RECORD_SCHEMA_PATH),
        "case": load_json(CASE_SCHEMA_PATH), "revision": load_json(REVISION_SCHEMA_PATH),
        "review_event": load_json(REVIEW_EVENT_SCHEMA_PATH), "saved_view": load_json(SAVED_VIEW_SCHEMA_PATH),
        "workspace_bundle": load_json(WORKSPACE_BUNDLE_SCHEMA_PATH),
        "knowledge_library": load_json(KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH),
        "catalyst_data": load_json(CATALYST_DATA_HANDOFF_SCHEMA_PATH),
    }
    fixtures = load_json(ROOT / "tests/fixtures/scoring-parity.json")
    sample_input = load_json(ROOT / "data/sample_narrative_risk_input.json")
    sample = load_json(ROOT / "outputs/sample_narrative_risk_output.json")
    sample_bundle = load_json(ROOT / "outputs/sample_case_bundle.json")
    legacy_v101 = load_json(ROOT / "tests/fixtures/legacy-v1.0.1-record.json")
    legacy_v110 = load_json(ROOT / "tests/fixtures/legacy-v1.1.0-record.json")
    legacy_v120 = load_json(ROOT / "tests/fixtures/legacy-v1.2.0-record.json")
    plugin = (ROOT / "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php").read_text(encoding="utf-8")
    workspace_js = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js").read_text(encoding="utf-8")

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
        "sample bundle": sample_bundle.get("bundle_version"),
    }
    mismatches = {name: value for name, value in versions.items() if value != VERSION}
    if mismatches:
        fail(f"version mismatch: {mismatches}")

    expected_ids = {
        "record": SCHEMA_ID,
        "input": INPUT_SCHEMA_ID,
        "ledger": LEDGER_SCHEMA_ID,
        "case": "https://sustainablecatalyst.com/schemas/narrative-risk/case/1.3.0",
        "revision": "https://sustainablecatalyst.com/schemas/narrative-risk/revision/1.3.0",
        "review_event": "https://sustainablecatalyst.com/schemas/narrative-risk/review-event/1.3.0",
        "saved_view": "https://sustainablecatalyst.com/schemas/narrative-risk/saved-view/1.3.0",
        "workspace_bundle": "https://sustainablecatalyst.com/schemas/narrative-risk/workspace-bundle/1.3.0",
    }
    identifiers = {
        "contract": contract.get("contract_id"), "Python contract": CONTRACT_ID,
        "manifest contract": manifest.get("contract_id"), "method": method.get("method_id"),
        "Python method": METHOD_ID, "manifest method": manifest.get("method_id"),
    }
    for name, expected in expected_ids.items():
        if schemas[name].get("$id") != expected:
            fail(f"{name} schema identifier mismatch")
        manifest_key = f"{name}_schema_id"
        contract_key = f"{name}_schema_id"
        if name in {"record", "input", "ledger", "case", "revision", "review_event", "saved_view", "workspace_bundle"}:
            if manifest.get(manifest_key) != expected:
                fail(f"manifest {name} schema identifier mismatch")
            if contract.get(contract_key) != expected:
                fail(f"contract {name} schema identifier mismatch")
        identifiers[f"{name} schema"] = expected

    if identifiers["contract"] != CONTRACT_ID or identifiers["Python contract"] != CONTRACT_ID or identifiers["manifest contract"] != CONTRACT_ID:
        fail("contract identifier mismatch")
    if identifiers["method"] != METHOD_ID or identifiers["Python method"] != METHOD_ID or identifiers["manifest method"] != METHOD_ID:
        fail("method identifier mismatch")
    if schemas["method"].get("$id") != contract.get("method_schema_id"):
        fail("method schema identifier mismatch")
    if contract.get("layers") != ["normalized_input", "evidence_ledger", "calculations", "interpretation", "human_decision"]:
        fail("canonical analytical layer order mismatch")
    if contract.get("compatibility", {}).get("migrates_from") != ["1.0.1", "1.1.0", "1.2.0"]:
        fail("legacy migration declarations are incomplete")
    if manifest.get("migration_sources") != ["1.0.1", "1.1.0", "1.2.0"]:
        fail("manifest migration sources are incomplete")
    if manifest.get("database") != "sqlite3" or "sqlite3" not in manifest.get("runtime_contracts", []):
        fail("SQLite runtime contract missing")
    if manifest.get("workspace_shortcodes") != ["[catalyst_narrative_risk_demo]", "[catalyst_narrative_risk_workspace]"]:
        fail("workspace shortcode manifest is incomplete")

    # Persistence must not silently change the analytical algorithm.
    for key in ("algorithm", "weights", "components", "interpretation", "ledger_policy"):
        previous = previous_method[key]
        current = method[key]
        if key == "ledger_policy":
            previous = dict(previous); current = dict(current)
            previous["policy_version"] = VERSION; current["policy_version"] = VERSION
        if previous != current:
            fail(f"v1.3.0 unexpectedly changed analytical method section: {key}")

    validate_method_snapshot(method)
    validate_narrative_risk_record(sample)
    if sample["normalized_input"]["claim"] != sample_input["claim"]:
        fail("sample input and output primary claim differ")
    if sha256_digest(method) != sample.get("method_snapshot_sha256"):
        fail("sample method snapshot digest mismatch")
    report = verify_record_reproducibility(sample)
    for key in ("exact_match", "method_snapshot_hash_match", "canonical_input_hash_match", "evidence_ledger_hash_match", "record_payload_hash_match"):
        if report[key] is not True:
            fail(f"sample reproducibility failed: {key}")

    validate_against_schema(sample_bundle, WORKSPACE_BUNDLE_SCHEMA_PATH)
    bundle_report = SQLiteCaseRepository.verify_bundle(sample_bundle)
    if not bundle_report["bundle_sha256_match"] or not bundle_report["all_revision_hashes_match"] or not bundle_report["all_case_ids_match"]:
        fail(f"sample workspace bundle verification failed: {bundle_report}")
    with tempfile.TemporaryDirectory() as temporary:
        repository = SQLiteCaseRepository(Path(temporary) / "import.sqlite3")
        imported = repository.import_case_bundle(sample_bundle)
        if imported["case"]["case_id"] != sample_bundle["case"]["case_id"]:
            fail("sample workspace bundle imported the wrong case")
        exported = repository.export_case_bundle(sample_bundle["case"]["case_id"], exported_at=sample_bundle["exported_at"])
        if exported != sample_bundle:
            fail("workspace bundle export/import round trip is not exact")
        if repository.health()["counts"] != {"cases": 1, "revisions": 1, "review_events": 1, "saved_views": 0, "activity": 3}:
            fail("workspace repository counts are unexpected")
        repository.close()

    migrated = [
        migrate_v1_0_1_record(legacy_v101, migrated_at="2026-07-17T14:00:00+00:00"),
        migrate_v1_1_0_record(legacy_v110, migrated_at="2026-07-17T15:00:00+00:00"),
        migrate_v1_2_0_record(legacy_v120, migrated_at="2026-07-17T16:00:00+00:00"),
    ]
    legacy_scores = [legacy_v101["risk_score"], legacy_v110["calculations"]["risk_score"], legacy_v120["calculations"]["risk_score"]]
    for record, score in zip(migrated, legacy_scores):
        if record["calculations"]["risk_score"] != score or not verify_record_reproducibility(record)["exact_match"]:
            fail("legacy migration did not preserve and reproduce the analytical result")
    if migrated[2]["evidence_ledger"]["relationships"] != legacy_v120["evidence_ledger"]["relationships"]:
        fail("v1.2.0 migration did not preserve evidence relationships")

    knowledge_handoff = load_json(ROOT / "data/handoffs/knowledge_library_source.json")
    data_handoff = load_json(ROOT / "data/handoffs/catalyst_data_source.json")
    validate_against_schema(knowledge_handoff, KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH)
    validate_against_schema(data_handoff, CATALYST_DATA_HANDOFF_SCHEMA_PATH)
    if import_knowledge_library_source(knowledge_handoff)["provenance"]["acquisition_method"] != "knowledge_library":
        fail("Knowledge Library handoff provenance mismatch")
    if import_catalyst_data_source(data_handoff)["provenance"]["acquisition_method"] != "catalyst_data":
        fail("Catalyst Data handoff provenance mismatch")

    if set(vocabs["vocabularies"]["case_status"]["values"]) != {"draft", "active", "in_review", "approved", "closed"}:
        fail("case-status vocabulary mismatch")
    if set(vocabs["vocabularies"]["review_event_type"]["values"]) != {"comment", "review_requested", "review_completed", "decision_updated", "status_changed", "assignment_changed"}:
        fail("review-event vocabulary mismatch")

    plugin_version = re.search(r"^ \* Version:\s*(\S+)", plugin, re.MULTILINE)
    if not plugin_version or plugin_version.group(1) != VERSION:
        fail("WordPress plugin header version mismatch")
    for token in ["catalyst_narrative_risk_demo", "catalyst_narrative_risk_workspace", "cnrisk-workspace-js", "array('cnrisk-engine-js')"]:
        if token not in plugin:
            fail(f"WordPress workspace token missing: {token}")
    for token in ["catalyst_narrative_risk_case_bundle", "localStorage", "revision_added", "bundle_sha256", "v1.3.0"]:
        if token not in workspace_js:
            fail(f"WordPress workspace behavior token missing: {token}")

    if len(fixtures.get("valid", [])) != 8 or len(fixtures.get("invalid", [])) != 23:
        fail("parity fixture matrix must contain exactly 8 valid and 23 invalid cases")

    for path in ROOT.rglob("*.json"):
        if any(part in {".git", ".venv", ".pytest_cache", "instance"} for part in path.parts):
            continue
        json.loads(path.read_text(encoding="utf-8"))
    committed_databases = [path for path in ROOT.rglob("*.sqlite3") if ".venv" not in path.parts and "instance" not in path.parts]
    if committed_databases:
        fail("runtime SQLite databases must not be included in the release repository")
    for output in [
        ROOT / "outputs/sample_narrative_risk_output.md", ROOT / "outputs/sample_source_list.md",
        ROOT / "outputs/sample_evidence_ledger.csv", ROOT / "outputs/sample_case_bundle.json",
    ]:
        if output.stat().st_size == 0:
            fail(f"empty sample output: {output.relative_to(ROOT)}")

    print("Catalyst Narrative Risk v1.3.0 release contract passed.")
    print(
        f"Version checks: {len(versions)}; identifier checks: {len(identifiers)}; "
        f"parity fixtures: {len(fixtures['valid'])} valid, {len(fixtures['invalid'])} invalid; "
        "workspace bundle round trip: exact."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
