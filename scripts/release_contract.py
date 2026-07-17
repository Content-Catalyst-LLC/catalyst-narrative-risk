#!/usr/bin/env python3
"""Validate the complete Catalyst Narrative Risk v1.6.0 release contract."""

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
    CATALYST_DATA_HANDOFF_SCHEMA_PATH, CASE_SCHEMA_PATH, INPUT_SCHEMA_PATH,
    KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH, LEDGER_SCHEMA_PATH, METHOD_SCHEMA_PATH,
    NARRATIVE_MAP_SCHEMA_PATH, RECORD_SCHEMA_PATH, REVIEW_ASSIGNMENT_SCHEMA_PATH,
    REVIEW_EVENT_SCHEMA_PATH, REVIEW_TEMPLATE_SCHEMA_PATH, GOVERNANCE_WORKFLOW_SCHEMA_PATH,
    GOVERNANCE_DECISION_SCHEMA_PATH, REVISION_SCHEMA_PATH, SAVED_VIEW_SCHEMA_PATH,
    WORKSPACE_BUNDLE_SCHEMA_PATH, MONITORING_SNAPSHOT_SCHEMA_PATH,
    MONITORING_COMPARISON_SCHEMA_PATH, WATCHLIST_SCHEMA_PATH, MONITORING_ALERT_SCHEMA_PATH,
    SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH,
    contract_definition, controlled_vocabularies, current_method_snapshot, load_json,
    sha256_digest, validate_against_schema,
)
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.migrations import (
    migrate_v1_0_1_record, migrate_v1_1_0_record, migrate_v1_2_0_record,
    migrate_v1_3_0_record, migrate_v1_4_0_record, migrate_v1_5_0_record,
)
from narrative_risk.governance import (
    ASSIGNMENT_STATUSES, GOVERNANCE_DISPOSITIONS, GOVERNANCE_ROLES,
    PERMISSIONS, PUBLICATION_RESTRICTIONS, REVIEW_STAGES,
)
from narrative_risk.narrative_map import LINK_TYPES, NODE_TYPES, SEVERITIES
from narrative_risk.service import (
    CONTRACT_ID, INPUT_SCHEMA_ID, LEDGER_SCHEMA_ID, METHOD_ID, NARRATIVE_MAP_SCHEMA_ID,
    SCHEMA_ID, VERSION, validate_method_snapshot, validate_narrative_risk_record,
    verify_record_reproducibility,
)
from narrative_risk.workspaces import SQLiteCaseRepository

REQUIRED_FILES = [
    "VERSION", "README.md", "CHANGELOG.md", "narrative_risk_manifest.json",
    "contracts/narrative-risk-contract.v1.6.0.json",
    "contracts/controlled-vocabularies.v1.6.0.json",
    "methods/transparent-heuristic.v1.6.0.json",
    "schemas/narrative_risk_input.schema.json", "schemas/narrative_risk_evidence_ledger.schema.json",
    "schemas/narrative_risk_narrative_map.schema.json", "schemas/narrative_risk_method_snapshot.schema.json",
    "schemas/narrative_risk_record.schema.json", "schemas/narrative_risk_case.schema.json",
    "schemas/narrative_risk_revision.schema.json", "schemas/narrative_risk_review_event.schema.json",
    "schemas/narrative_risk_review_assignment.schema.json", "schemas/narrative_risk_governance_workflow.schema.json",
    "schemas/narrative_risk_governance_decision.schema.json", "schemas/narrative_risk_review_template.schema.json",
    "schemas/narrative_risk_saved_view.schema.json", "schemas/narrative_risk_workspace_bundle.schema.json",
    "schemas/knowledge_library_source_handoff.schema.json", "schemas/catalyst_data_source_handoff.schema.json",
    "schemas/narrative_risk_monitoring_snapshot.schema.json", "schemas/narrative_risk_monitoring_comparison.schema.json",
    "schemas/narrative_risk_watchlist.schema.json", "schemas/narrative_risk_monitoring_alert.schema.json",
    "schemas/site_intelligence_monitoring_handoff.schema.json",
    "schemas/archive/narrative_risk_record.v1.3.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.3.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.3.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.3.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.4.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.4.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.4.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.4.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.4.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.5.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.5.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.5.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.5.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.5.0.schema.json",
    "narrative_risk/contracts.py", "narrative_risk/service.py", "narrative_risk/ledger.py",
    "narrative_risk/narrative_map.py", "narrative_risk/integrations.py",
    "narrative_risk/governance.py", "narrative_risk/monitoring.py", "narrative_risk/migrations.py", "narrative_risk/workspaces.py",
    "python/narrative_risk_brief.py", "python/export_evidence_ledger.py",
    "python/export_narrative_map.py", "python/migrate_narrative_risk_record.py",
    "python/verify_narrative_risk_record.py", "python/narrative_risk_workspace.py",
    "data/sample_narrative_risk_input.json",
    "outputs/sample_narrative_risk_output.json", "outputs/sample_narrative_risk_output.md",
    "outputs/sample_source_list.md", "outputs/sample_evidence_ledger.csv",
    "outputs/sample_narrative_map.md", "outputs/sample_narrative_map.mmd",
    "outputs/sample_case_bundle.json",
    "tests/fixtures/scoring-parity.json", "tests/fixtures/legacy-v1.0.1-record.json",
    "tests/fixtures/legacy-v1.1.0-record.json", "tests/fixtures/legacy-v1.2.0-record.json",
    "tests/fixtures/legacy-v1.3.0-record.json", "tests/fixtures/legacy-v1.4.0-record.json",
    "tests/fixtures/legacy-v1.5.0-record.json",
    "tests/test_narrative_map.py", "tests/test_workspaces.py", "tests/test_governance.py", "tests/test_monitoring.py",
    "scripts/generate_browser_method_asset.py", "scripts/cross_runtime_record_parity.py",
    "scripts/cross_runtime_parity.py", "scripts/test_browser_engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-map.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js",
    "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php",
    "release/v1.6.0.md", "docs/review-approval-governance-workflow.md",
    "docs/migration-v1.4.0.md", "docs/migration-v1.5.0.md", "docs/canonical-contract.md", "docs/reproducibility.md",
    "docs/narrative-change-freshness-monitoring.md", "docs/site-intelligence-monitoring-handoff.md",
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
    previous_method = load_json(ROOT / "methods/transparent-heuristic.v1.5.0.json")
    schemas = {
        "input": load_json(INPUT_SCHEMA_PATH), "ledger": load_json(LEDGER_SCHEMA_PATH),
        "narrative_map": load_json(NARRATIVE_MAP_SCHEMA_PATH), "method": load_json(METHOD_SCHEMA_PATH),
        "record": load_json(RECORD_SCHEMA_PATH), "case": load_json(CASE_SCHEMA_PATH),
        "revision": load_json(REVISION_SCHEMA_PATH), "review_event": load_json(REVIEW_EVENT_SCHEMA_PATH),
        "review_assignment": load_json(REVIEW_ASSIGNMENT_SCHEMA_PATH),
        "governance_workflow": load_json(GOVERNANCE_WORKFLOW_SCHEMA_PATH),
        "governance_decision": load_json(GOVERNANCE_DECISION_SCHEMA_PATH),
        "review_template": load_json(REVIEW_TEMPLATE_SCHEMA_PATH),
        "saved_view": load_json(SAVED_VIEW_SCHEMA_PATH), "workspace_bundle": load_json(WORKSPACE_BUNDLE_SCHEMA_PATH),
        "knowledge_library": load_json(KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH),
        "catalyst_data": load_json(CATALYST_DATA_HANDOFF_SCHEMA_PATH),
        "monitoring_snapshot": load_json(MONITORING_SNAPSHOT_SCHEMA_PATH),
        "monitoring_comparison": load_json(MONITORING_COMPARISON_SCHEMA_PATH),
        "watchlist": load_json(WATCHLIST_SCHEMA_PATH),
        "monitoring_alert": load_json(MONITORING_ALERT_SCHEMA_PATH),
        "site_intelligence_handoff": load_json(SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH),
    }
    fixtures = load_json(ROOT / "tests/fixtures/scoring-parity.json")
    sample_input = load_json(ROOT / "data/sample_narrative_risk_input.json")
    sample = load_json(ROOT / "outputs/sample_narrative_risk_output.json")
    sample_bundle = load_json(ROOT / "outputs/sample_case_bundle.json")
    legacy = {
        "1.0.1": load_json(ROOT / "tests/fixtures/legacy-v1.0.1-record.json"),
        "1.1.0": load_json(ROOT / "tests/fixtures/legacy-v1.1.0-record.json"),
        "1.2.0": load_json(ROOT / "tests/fixtures/legacy-v1.2.0-record.json"),
        "1.3.0": load_json(ROOT / "tests/fixtures/legacy-v1.3.0-record.json"),
        "1.4.0": load_json(ROOT / "tests/fixtures/legacy-v1.4.0-record.json"),
        "1.5.0": load_json(ROOT / "tests/fixtures/legacy-v1.5.0-record.json"),
    }
    plugin = (ROOT / "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php").read_text(encoding="utf-8")
    workspace_js = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js").read_text(encoding="utf-8")
    demo_js = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js").read_text(encoding="utf-8")

    versions = {
        "VERSION": version_file, "Python VERSION": VERSION, "manifest": manifest.get("version"),
        "manifest contract": manifest.get("contract_version"), "manifest method": manifest.get("method_version"),
        "manifest schema": manifest.get("schema_version"), "manifest vocabulary": manifest.get("controlled_vocabulary_version"),
        "contract": contract.get("contract_version"), "contract method": contract.get("method_version"),
        "contract vocabulary": contract.get("controlled_vocabulary_version"), "method": method.get("method_version"),
        "ledger policy": method.get("ledger_policy", {}).get("policy_version"),
        "map policy": method.get("narrative_map_policy", {}).get("policy_version"),
        "governance policy": method.get("governance_policy", {}).get("policy_version"),
        "monitoring policy": method.get("monitoring_policy", {}).get("policy_version"),
        "vocabulary": vocabs.get("vocabulary_version"), "fixture": fixtures.get("contract_version"),
        "sample contract": sample.get("contract", {}).get("contract_version"),
        "sample method": sample.get("method_snapshot", {}).get("method_version"),
        "sample ledger": sample.get("evidence_ledger", {}).get("ledger_version"),
        "sample map": sample.get("narrative_map", {}).get("map_version"),
        "sample bundle": sample_bundle.get("bundle_version"),
    }
    mismatches = {name: value for name, value in versions.items() if value != VERSION}
    if mismatches:
        fail(f"version mismatch: {mismatches}")

    expected_ids = {
        "record": SCHEMA_ID, "input": INPUT_SCHEMA_ID, "ledger": LEDGER_SCHEMA_ID,
        "narrative_map": NARRATIVE_MAP_SCHEMA_ID,
        "case": f"https://sustainablecatalyst.com/schemas/narrative-risk/case/{VERSION}",
        "revision": f"https://sustainablecatalyst.com/schemas/narrative-risk/revision/{VERSION}",
        "review_event": f"https://sustainablecatalyst.com/schemas/narrative-risk/review-event/{VERSION}",
        "review_assignment": f"https://sustainablecatalyst.com/schemas/narrative-risk/review-assignment/{VERSION}",
        "governance_workflow": f"https://sustainablecatalyst.com/schemas/narrative-risk/governance-workflow/{VERSION}",
        "governance_decision": f"https://sustainablecatalyst.com/schemas/narrative-risk/governance-decision/{VERSION}",
        "review_template": f"https://sustainablecatalyst.com/schemas/narrative-risk/review-template/{VERSION}",
        "saved_view": f"https://sustainablecatalyst.com/schemas/narrative-risk/saved-view/{VERSION}",
        "workspace_bundle": f"https://sustainablecatalyst.com/schemas/narrative-risk/workspace-bundle/{VERSION}",
        "monitoring_snapshot": f"https://sustainablecatalyst.com/schemas/narrative-risk/monitoring-snapshot/{VERSION}",
        "monitoring_comparison": f"https://sustainablecatalyst.com/schemas/narrative-risk/monitoring-comparison/{VERSION}",
        "watchlist": f"https://sustainablecatalyst.com/schemas/narrative-risk/watchlist/{VERSION}",
        "monitoring_alert": f"https://sustainablecatalyst.com/schemas/narrative-risk/monitoring-alert/{VERSION}",
    }
    identifiers = {"contract": CONTRACT_ID, "method": METHOD_ID}
    if contract.get("contract_id") != CONTRACT_ID or manifest.get("contract_id") != CONTRACT_ID:
        fail("contract identifier mismatch")
    if method.get("method_id") != METHOD_ID or manifest.get("method_id") != METHOD_ID:
        fail("method identifier mismatch")
    for name, expected in expected_ids.items():
        if schemas[name].get("$id") != expected:
            fail(f"{name} schema identifier mismatch")
        if manifest.get(f"{name}_schema_id") != expected:
            fail(f"manifest {name} schema identifier mismatch")
        if contract.get(f"{name}_schema_id") != expected:
            fail(f"contract {name} schema identifier mismatch")
        identifiers[name] = expected
    if schemas["method"].get("$id") != contract.get("method_schema_id") or manifest.get("method_schema_id") != schemas["method"].get("$id"):
        fail("method schema identifier mismatch")
    if contract.get("layers") != ["normalized_input", "evidence_ledger", "narrative_map", "calculations", "interpretation", "human_decision"]:
        fail("canonical six-layer order mismatch")
    migration_sources = ["1.0.1", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0"]
    if contract.get("compatibility", {}).get("migrates_from") != migration_sources or manifest.get("migration_sources") != migration_sources:
        fail("legacy migration declarations are incomplete")
    if manifest.get("database") != "sqlite3" or "sqlite3" not in manifest.get("runtime_contracts", []):
        fail("SQLite runtime contract missing")
    if manifest.get("workspace_shortcodes") != ["[catalyst_narrative_risk_demo]", "[catalyst_narrative_risk_workspace]"]:
        fail("workspace shortcode manifest is incomplete")

    # Monitoring remains separate and must not silently change the v1.5 analytical or governance engine.
    for key in ("algorithm", "weights", "components", "interpretation", "ledger_policy", "narrative_map_policy", "governance_policy"):
        previous = json.loads(json.dumps(previous_method[key]))
        current = json.loads(json.dumps(method[key]))
        if key.endswith("policy"):
            previous["policy_version"] = VERSION
            current["policy_version"] = VERSION
        if previous != current:
            fail(f"v1.6.0 unexpectedly changed analytical scoring section: {key}")
    policy = method.get("narrative_map_policy", {})
    if tuple(policy.get("node_types", [])) != NODE_TYPES:
        fail("narrative node vocabulary and method policy differ")
    if tuple(policy.get("link_types", [])) != LINK_TYPES:
        fail("narrative link vocabulary and method policy differ")
    if tuple(policy.get("issue_severities", [])) != SEVERITIES:
        fail("narrative issue severity vocabulary and method policy differ")
    if set(vocabs["vocabularies"]["narrative_node_type"]["values"]) != set(NODE_TYPES):
        fail("controlled narrative-node vocabulary mismatch")
    if set(vocabs["vocabularies"]["narrative_link_type"]["values"]) != set(LINK_TYPES):
        fail("controlled narrative-link vocabulary mismatch")

    governance = method.get("governance_policy", {})
    if tuple(governance.get("stage_order", [])) != REVIEW_STAGES:
        fail("governance review stages and method policy differ")
    if set(governance.get("roles", [])) != GOVERNANCE_ROLES:
        fail("governance roles and method policy differ")
    declared_permissions = {value for values in governance.get("permissions", {}).values() for value in values}
    if not declared_permissions <= PERMISSIONS or not {"approve_final", "manage_templates", "assign_reviewers"} <= declared_permissions:
        fail("governance permission policy is incomplete")
    if set(schemas["review_assignment"]["properties"]["status"]["enum"]) != ASSIGNMENT_STATUSES:
        fail("review-assignment status schema differs from governance implementation")
    if set(schemas["governance_decision"]["properties"]["disposition"]["enum"]) != GOVERNANCE_DISPOSITIONS:
        fail("governance decision schema differs from governance implementation")
    if set(schemas["governance_decision"]["properties"]["publication_restrictions"]["items"]["enum"]) != PUBLICATION_RESTRICTIONS:
        fail("publication restriction schema differs from governance implementation")

    validate_method_snapshot(method)
    validate_narrative_risk_record(sample)
    if sample["normalized_input"]["claim"] != sample_input["claim"]:
        fail("sample input and output primary claim differ")
    if sha256_digest(method) != sample.get("method_snapshot_sha256"):
        fail("sample method snapshot digest mismatch")
    report = verify_record_reproducibility(sample)
    checks = (
        "exact_match", "method_snapshot_hash_match", "canonical_input_hash_match",
        "evidence_ledger_hash_match", "narrative_map_hash_match", "record_payload_hash_match",
    )
    if not all(report[key] is True for key in checks):
        fail(f"sample reproducibility failed: {report}")
    summary = sample["narrative_map"]["analysis"]["summary"]
    if summary["node_count"] < 3 or summary["link_count"] < 2 or not sample["narrative_map"]["wording_comparisons"]:
        fail("canonical sample does not exercise decomposition, links, and wording comparison")

    validate_against_schema(sample_bundle, WORKSPACE_BUNDLE_SCHEMA_PATH)
    bundle_report = SQLiteCaseRepository.verify_bundle(sample_bundle)
    if not all(bundle_report[key] for key in ("bundle_sha256_match", "all_revision_hashes_match", "all_case_ids_match")):
        fail(f"sample workspace bundle verification failed: {bundle_report}")
    if sample_bundle["governance_workflow"] is None or not sample_bundle["review_assignments"] or not sample_bundle["governance_decisions"]:
        fail("sample workspace bundle must exercise governed review records")
    if sample_bundle["governance_workflow"]["status"] != "approved":
        fail("sample governance workflow is not approved")
    if sample_bundle["case"]["final_disposition"] != "approve_with_conditions":
        fail("sample case does not demonstrate conditional approval")
    if not sample_bundle["governance_workflow"]["publication_allowed"]:
        fail("sample conditional approval should permit publication with controls")
    if not sample_bundle["monitoring_snapshots"] or not sample_bundle["watchlists"] or not sample_bundle["monitoring_alerts"]:
        fail("sample workspace bundle must exercise snapshots, watchlists, and monitoring alerts")
    if not sample_bundle["monitoring_comparisons"]:
        fail("sample workspace bundle must exercise narrative-change comparison")
    with tempfile.TemporaryDirectory() as temporary:
        repository = SQLiteCaseRepository(Path(temporary) / "import.sqlite3")
        repository.import_case_bundle(sample_bundle)
        exported = repository.export_case_bundle(sample_bundle["case"]["case_id"], exported_at=sample_bundle["exported_at"])
        if exported != sample_bundle:
            fail("workspace bundle export/import round trip is not exact")
        repository.close()

    migration_functions = {
        "1.0.1": migrate_v1_0_1_record, "1.1.0": migrate_v1_1_0_record,
        "1.2.0": migrate_v1_2_0_record, "1.3.0": migrate_v1_3_0_record,
        "1.4.0": migrate_v1_4_0_record, "1.5.0": migrate_v1_5_0_record,
    }
    for index, version in enumerate(migration_sources, start=1):
        source = legacy[version]
        migrated = migration_functions[version](source, migrated_at=f"2026-07-17T{13+index:02d}:00:00+00:00")
        old_score = source["risk_score"] if version == "1.0.1" else source["calculations"]["risk_score"]
        old_level = source["risk_level"] if version == "1.0.1" else source["interpretation"]["risk_level"]
        if migrated["calculations"]["risk_score"] != old_score or migrated["interpretation"]["risk_level"] != old_level:
            fail(f"v{version} migration changed analytical result")
        if not verify_record_reproducibility(migrated)["exact_match"]:
            fail(f"v{version} migration is not exactly reproducible")
    migrated_v130 = migrate_v1_3_0_record(legacy["1.3.0"], migrated_at="2026-07-17T18:00:00+00:00")
    old_ledger = json.loads(json.dumps(legacy["1.3.0"]["evidence_ledger"]))
    new_ledger = json.loads(json.dumps(migrated_v130["evidence_ledger"]))
    old_ledger["ledger_version"] = VERSION
    old_ledger["derived_scoring_inputs"]["basis"] = new_ledger["derived_scoring_inputs"]["basis"]
    if old_ledger != new_ledger:
        fail("v1.3.0 migration did not preserve evidence-ledger content")
    if len(migrated_v130["narrative_map"]["nodes"]) != len(legacy["1.3.0"]["evidence_ledger"]["claims"]):
        fail("v1.3.0 migration did not map ledger claims deterministically")

    knowledge_handoff = load_json(ROOT / "data/handoffs/knowledge_library_source.json")
    data_handoff = load_json(ROOT / "data/handoffs/catalyst_data_source.json")
    validate_against_schema(knowledge_handoff, KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH)
    validate_against_schema(data_handoff, CATALYST_DATA_HANDOFF_SCHEMA_PATH)
    if import_knowledge_library_source(knowledge_handoff)["provenance"]["acquisition_method"] != "knowledge_library":
        fail("Knowledge Library handoff provenance mismatch")
    if import_catalyst_data_source(data_handoff)["provenance"]["acquisition_method"] != "catalyst_data":
        fail("Catalyst Data handoff provenance mismatch")

    plugin_version = re.search(r"^ \* Version:\s*(\S+)", plugin, re.MULTILINE)
    if not plugin_version or plugin_version.group(1) != VERSION:
        fail("WordPress plugin header version mismatch")
    for token in ["catalyst_narrative_risk_demo", "catalyst_narrative_risk_workspace", "cnrisk-map-js", "narrative-risk-map.js", "array('cnrisk-method-js', 'cnrisk-map-js')"]:
        if token not in plugin:
            fail(f"WordPress narrative-map token missing: {token}")
    for token in ["narrative_map_json", "data-cnrisk-map-summary", "narrative_map"]:
        if token not in plugin + demo_js:
            fail(f"WordPress map-interface token missing: {token}")
    for token in ["catalyst_narrative_risk_case_bundle", "localStorage", "revision_added", "bundle_sha256", "governance_workflow", "review_assignments", "governance_decisions", "publication_allowed", "monitoring_snapshots", "watchlists", "monitoring_alerts", "material_change", "data-cnrisk-run-watch", "v1.6.0"]:
        if token not in workspace_js:
            fail(f"WordPress workspace behavior token missing: {token}")

    if len(fixtures.get("valid", [])) != 10 or len(fixtures.get("invalid", [])) != 32:
        fail("parity fixture matrix must contain exactly 10 valid and 32 invalid cases")
    for path in ROOT.rglob("*.json"):
        if any(part in {".git", ".venv", ".pytest_cache", "instance"} for part in path.parts):
            continue
        json.loads(path.read_text(encoding="utf-8"))
    committed_databases = [path for path in ROOT.rglob("*.sqlite3") if ".venv" not in path.parts and "instance" not in path.parts]
    if committed_databases:
        fail("runtime SQLite databases must not be included in the release repository")
    for output in [
        ROOT / "outputs/sample_narrative_risk_output.md", ROOT / "outputs/sample_source_list.md",
        ROOT / "outputs/sample_evidence_ledger.csv", ROOT / "outputs/sample_narrative_map.md",
        ROOT / "outputs/sample_narrative_map.mmd", ROOT / "outputs/sample_case_bundle.json",
    ]:
        if output.stat().st_size == 0:
            fail(f"empty sample output: {output.relative_to(ROOT)}")

    print("Catalyst Narrative Risk v1.6.0 release contract passed.")
    print(
        f"Version checks: {len(versions)}; identifier checks: {len(identifiers)}; "
        f"parity fixtures: {len(fixtures['valid'])} valid, {len(fixtures['invalid'])} invalid; "
        "six-layer reproduction and workspace bundle round trip: exact."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
