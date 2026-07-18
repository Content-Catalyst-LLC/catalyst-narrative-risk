#!/usr/bin/env python3
"""Validate the complete Catalyst Narrative Risk v2.0.0 release contract."""

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
    SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH, STAKEHOLDER_ACTOR_SCHEMA_PATH,
    STAKEHOLDER_RELATIONSHIP_SCHEMA_PATH, STAKEHOLDER_INCENTIVE_SCHEMA_PATH,
    STAKEHOLDER_PRESSURE_SCHEMA_PATH, STAKEHOLDER_CONSEQUENCE_SCHEMA_PATH,
    STAKEHOLDER_INTELLIGENCE_SCHEMA_PATH, CATALYST_CANVAS_STAKEHOLDER_HANDOFF_SCHEMA_PATH,
    COMPARISON_SET_SCHEMA_PATH, COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH,
    SCENARIO_SCHEMA_PATH, SCENARIO_RESULT_SCHEMA_PATH, SENSITIVITY_ANALYSIS_SCHEMA_PATH,
    COMPARATIVE_PORTFOLIO_SCHEMA_PATH, DECISION_STUDIO_HANDOFF_SCHEMA_PATH,
    BRIEFING_SCHEMA_PATH, PUBLICATION_PACKAGE_SCHEMA_PATH, PUBLIC_EMBED_SCHEMA_PATH,
    API_KEY_SCHEMA_PATH, PLATFORM_HANDOFF_SCHEMA_PATH,
    SECURITY_REPORT_SCHEMA_PATH, PRIVACY_POLICY_SCHEMA_PATH, RETENTION_ASSESSMENT_SCHEMA_PATH,
    BACKUP_MANIFEST_SCHEMA_PATH, ACCESSIBILITY_REPORT_SCHEMA_PATH, PERFORMANCE_REPORT_SCHEMA_PATH,
    PRODUCTION_READINESS_SCHEMA_PATH, PLATFORM_PROFILE_SCHEMA_PATH, PLATFORM_EVENT_SCHEMA_PATH,
    INTEGRATION_ROUTE_SCHEMA_PATH, CONNECTED_DOSSIER_SCHEMA_PATH, INSTITUTIONAL_WORKSPACE_SCHEMA_PATH,
    contract_definition, controlled_vocabularies, current_method_snapshot, load_json,
    sha256_digest, validate_against_schema,
)
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source
from narrative_risk.comparisons import (
    COMPARISON_STATUSES, COMPARISON_MODES, SCENARIO_TYPES, SCENARIO_STATUSES,
    SENSITIVITY_DIMENSIONS,
)
from narrative_risk.migrations import (
    migrate_v1_0_1_record, migrate_v1_1_0_record, migrate_v1_2_0_record,
    migrate_v1_3_0_record, migrate_v1_4_0_record, migrate_v1_5_0_record, migrate_v1_6_0_record,
    migrate_v1_7_0_record, migrate_v1_8_0_record, migrate_v1_9_0_record, migrate_v1_10_0_record,
)
from narrative_risk.governance import (
    ASSIGNMENT_STATUSES, GOVERNANCE_DISPOSITIONS, GOVERNANCE_ROLES,
    PERMISSIONS, PUBLICATION_RESTRICTIONS, REVIEW_STAGES,
)
from narrative_risk.narrative_map import LINK_TYPES, NODE_TYPES, SEVERITIES
from narrative_risk.publication import AUDIENCES, CLASSIFICATIONS, FORMATS, PACKAGE_STATUSES, EMBED_STATUSES, API_SCOPES, PLATFORM_TARGETS
from narrative_risk.stakeholders import (
    ACTOR_TYPES, RELATIONSHIP_TYPES, INCENTIVE_TYPES, PRESSURE_TYPES, IMPACT_TYPES,
    validate_canvas_handoff,
)
from narrative_risk.service import (
    CONTRACT_ID, INPUT_SCHEMA_ID, LEDGER_SCHEMA_ID, METHOD_ID, NARRATIVE_MAP_SCHEMA_ID,
    SCHEMA_ID, VERSION, validate_method_snapshot, validate_narrative_risk_record,
    verify_record_reproducibility,
)
from narrative_risk.workspaces import SQLiteCaseRepository
from narrative_risk.connected import MODULES, EVENT_TYPES, ROUTE_STATUSES

REQUIRED_FILES = [
    "VERSION", "README.md", "CHANGELOG.md", "narrative_risk_manifest.json",
    "contracts/narrative-risk-contract.v2.0.0.json",
    "contracts/controlled-vocabularies.v2.0.0.json",
    "methods/transparent-heuristic.v2.0.0.json",
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
    "schemas/narrative_risk_stakeholder_actor.schema.json",
    "schemas/narrative_risk_stakeholder_relationship.schema.json",
    "schemas/narrative_risk_stakeholder_incentive.schema.json",
    "schemas/narrative_risk_stakeholder_pressure.schema.json",
    "schemas/narrative_risk_stakeholder_consequence.schema.json",
    "schemas/narrative_risk_stakeholder_intelligence.schema.json",
    "schemas/catalyst_canvas_stakeholder_handoff.schema.json",
    "schemas/narrative_risk_comparison_set.schema.json",
    "schemas/narrative_risk_comparative_evidence_matrix.schema.json",
    "schemas/narrative_risk_scenario.schema.json",
    "schemas/narrative_risk_scenario_result.schema.json",
    "schemas/narrative_risk_sensitivity_analysis.schema.json",
    "schemas/narrative_risk_comparative_portfolio.schema.json",
    "schemas/narrative_risk_decision_studio_handoff.schema.json",
    "schemas/narrative_risk_briefing.schema.json", "schemas/narrative_risk_publication_package.schema.json",
    "schemas/narrative_risk_public_embed.schema.json", "schemas/narrative_risk_api_key.schema.json",
    "schemas/narrative_risk_platform_handoff.schema.json",
    "schemas/narrative_risk_security_report.schema.json", "schemas/narrative_risk_privacy_policy.schema.json",
    "schemas/narrative_risk_retention_assessment.schema.json", "schemas/narrative_risk_backup_manifest.schema.json",
    "schemas/narrative_risk_accessibility_report.schema.json", "schemas/narrative_risk_performance_report.schema.json",
    "schemas/narrative_risk_production_readiness.schema.json",
    "schemas/narrative_risk_platform_profile.schema.json", "schemas/narrative_risk_platform_event.schema.json",
    "schemas/narrative_risk_integration_route.schema.json", "schemas/narrative_risk_connected_dossier.schema.json",
    "schemas/narrative_risk_institutional_workspace.schema.json",
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
    "schemas/archive/narrative_risk_record.v1.6.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.6.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.6.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.6.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.6.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.7.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.7.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.7.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.7.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.7.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.8.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.8.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.8.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.8.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.8.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.9.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.9.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.9.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.9.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.9.0.schema.json",
    "schemas/archive/narrative_risk_record.v1.10.0.schema.json",
    "schemas/archive/narrative_risk_input.v1.10.0.schema.json",
    "schemas/archive/narrative_risk_evidence_ledger.v1.10.0.schema.json",
    "schemas/archive/narrative_risk_narrative_map.v1.10.0.schema.json",
    "schemas/archive/narrative_risk_method_snapshot.v1.10.0.schema.json",
    "narrative_risk/contracts.py", "narrative_risk/service.py", "narrative_risk/ledger.py",
    "narrative_risk/narrative_map.py", "narrative_risk/integrations.py",
    "narrative_risk/governance.py", "narrative_risk/monitoring.py", "narrative_risk/stakeholders.py", "narrative_risk/comparisons.py", "narrative_risk/publication.py", "narrative_risk/hardening.py", "narrative_risk/connected.py", "narrative_risk/migrations.py", "narrative_risk/workspaces.py",
    "python/narrative_risk_brief.py", "python/export_evidence_ledger.py",
    "python/export_narrative_map.py", "python/migrate_narrative_risk_record.py",
    "python/verify_narrative_risk_record.py", "python/narrative_risk_workspace.py",
    "data/sample_narrative_risk_input.json",
    "outputs/sample_narrative_risk_output.json", "outputs/sample_narrative_risk_output.md",
    "outputs/sample_source_list.md", "outputs/sample_evidence_ledger.csv",
    "outputs/sample_narrative_map.md", "outputs/sample_narrative_map.mmd",
    "outputs/sample_case_bundle.json", "outputs/sample_public_brief.json", "outputs/sample_public_brief.md",
    "outputs/sample_public_brief.html", "outputs/sample_public_brief.pdf", "outputs/sample_public_brief.csv", "outputs/sample_public_brief.jsonld",
    "outputs/sample_platform_profile.json", "outputs/sample_connected_dossier.json", "outputs/sample_institutional_workspace.json",
    "tests/fixtures/scoring-parity.json", "tests/fixtures/legacy-v1.0.1-record.json",
    "tests/fixtures/legacy-v1.1.0-record.json", "tests/fixtures/legacy-v1.2.0-record.json",
    "tests/fixtures/legacy-v1.3.0-record.json", "tests/fixtures/legacy-v1.4.0-record.json",
    "tests/fixtures/legacy-v1.5.0-record.json", "tests/fixtures/legacy-v1.6.0-record.json", "tests/fixtures/legacy-v1.7.0-record.json", "tests/fixtures/legacy-v1.8.0-record.json", "tests/fixtures/legacy-v1.9.0-record.json", "tests/fixtures/legacy-v1.10.0-record.json",
    "tests/test_narrative_map.py", "tests/test_workspaces.py", "tests/test_governance.py", "tests/test_monitoring.py", "tests/test_stakeholders.py", "tests/test_comparisons.py", "tests/test_publication.py", "tests/test_hardening.py", "tests/test_connected.py",
    "scripts/generate_browser_method_asset.py", "scripts/cross_runtime_record_parity.py",
    "scripts/cross_runtime_parity.py", "scripts/test_browser_engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-map.js",
    "wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-publication.js",
    "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-publication.css",
    "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php",
    "release/v2.0.0.md", "docs/review-approval-governance-workflow.md",
    "docs/migration-v1.4.0.md", "docs/migration-v1.5.0.md", "docs/canonical-contract.md", "docs/reproducibility.md",
    "docs/narrative-change-freshness-monitoring.md", "docs/site-intelligence-monitoring-handoff.md",
    "docs/stakeholder-incentive-pressure-intelligence.md", "docs/catalyst-canvas-stakeholder-handoff.md", "docs/migration-v1.6.0.md",
    "docs/comparative-narratives-scenario-analysis.md", "docs/decision-studio-handoff.md", "docs/migration-v1.7.0.md",
    "docs/briefing-publication-api-platform-integration.md", "docs/openapi.md", "docs/wordpress-publication.md", "docs/migration-v1.8.0.md",
    "docs/connected-narrative-risk-platform.md", "docs/migration-v1.10.0.md",
    "data/handoffs/catalyst_canvas_stakeholder_handoff.json",
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
    previous_method = load_json(ROOT / "methods/transparent-heuristic.v1.10.0.json")
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
        "stakeholder_actor": load_json(STAKEHOLDER_ACTOR_SCHEMA_PATH),
        "stakeholder_relationship": load_json(STAKEHOLDER_RELATIONSHIP_SCHEMA_PATH),
        "stakeholder_incentive": load_json(STAKEHOLDER_INCENTIVE_SCHEMA_PATH),
        "stakeholder_pressure": load_json(STAKEHOLDER_PRESSURE_SCHEMA_PATH),
        "stakeholder_consequence": load_json(STAKEHOLDER_CONSEQUENCE_SCHEMA_PATH),
        "stakeholder_intelligence": load_json(STAKEHOLDER_INTELLIGENCE_SCHEMA_PATH),
        "catalyst_canvas_stakeholder_handoff": load_json(CATALYST_CANVAS_STAKEHOLDER_HANDOFF_SCHEMA_PATH),
        "comparison_set": load_json(COMPARISON_SET_SCHEMA_PATH),
        "comparative_evidence_matrix": load_json(COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH),
        "scenario": load_json(SCENARIO_SCHEMA_PATH),
        "scenario_result": load_json(SCENARIO_RESULT_SCHEMA_PATH),
        "sensitivity_analysis": load_json(SENSITIVITY_ANALYSIS_SCHEMA_PATH),
        "comparative_portfolio": load_json(COMPARATIVE_PORTFOLIO_SCHEMA_PATH),
        "decision_studio_handoff": load_json(DECISION_STUDIO_HANDOFF_SCHEMA_PATH),
        "briefing": load_json(BRIEFING_SCHEMA_PATH),
        "publication_package": load_json(PUBLICATION_PACKAGE_SCHEMA_PATH),
        "public_embed": load_json(PUBLIC_EMBED_SCHEMA_PATH),
        "api_key": load_json(API_KEY_SCHEMA_PATH),
        "platform_handoff": load_json(PLATFORM_HANDOFF_SCHEMA_PATH),
        "security_report": load_json(SECURITY_REPORT_SCHEMA_PATH),
        "privacy_policy": load_json(PRIVACY_POLICY_SCHEMA_PATH),
        "retention_assessment": load_json(RETENTION_ASSESSMENT_SCHEMA_PATH),
        "backup_manifest": load_json(BACKUP_MANIFEST_SCHEMA_PATH),
        "accessibility_report": load_json(ACCESSIBILITY_REPORT_SCHEMA_PATH),
        "performance_report": load_json(PERFORMANCE_REPORT_SCHEMA_PATH),
        "production_readiness": load_json(PRODUCTION_READINESS_SCHEMA_PATH),
        "platform_profile": load_json(PLATFORM_PROFILE_SCHEMA_PATH),
        "platform_event": load_json(PLATFORM_EVENT_SCHEMA_PATH),
        "integration_route": load_json(INTEGRATION_ROUTE_SCHEMA_PATH),
        "connected_dossier": load_json(CONNECTED_DOSSIER_SCHEMA_PATH),
        "institutional_workspace": load_json(INSTITUTIONAL_WORKSPACE_SCHEMA_PATH),
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
        "1.6.0": load_json(ROOT / "tests/fixtures/legacy-v1.6.0-record.json"),
        "1.7.0": load_json(ROOT / "tests/fixtures/legacy-v1.7.0-record.json"),
        "1.8.0": load_json(ROOT / "tests/fixtures/legacy-v1.8.0-record.json"),
        "1.9.0": load_json(ROOT / "tests/fixtures/legacy-v1.9.0-record.json"),
        "1.10.0": load_json(ROOT / "tests/fixtures/legacy-v1.10.0-record.json"),
    }
    plugin = (ROOT / "wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php").read_text(encoding="utf-8")
    workspace_js = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js").read_text(encoding="utf-8")
    publication_js = (ROOT / "wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-publication.js").read_text(encoding="utf-8")
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
        "stakeholder policy": method.get("stakeholder_policy", {}).get("policy_version"),
        "comparative policy": method.get("comparative_policy", {}).get("policy_version"),
        "publication policy": method.get("publication_policy", {}).get("policy_version"),
        "hardening policy": method.get("hardening_policy", {}).get("policy_version"),
        "connected platform policy": method.get("connected_platform_policy", {}).get("policy_version"),
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
        "stakeholder_actor": f"https://sustainablecatalyst.com/schemas/narrative-risk/stakeholder-actor/{VERSION}",
        "stakeholder_relationship": f"https://sustainablecatalyst.com/schemas/narrative-risk/stakeholder-relationship/{VERSION}",
        "stakeholder_incentive": f"https://sustainablecatalyst.com/schemas/narrative-risk/stakeholder-incentive/{VERSION}",
        "stakeholder_pressure": f"https://sustainablecatalyst.com/schemas/narrative-risk/stakeholder-pressure/{VERSION}",
        "stakeholder_consequence": f"https://sustainablecatalyst.com/schemas/narrative-risk/stakeholder-consequence/{VERSION}",
        "stakeholder_intelligence": f"https://sustainablecatalyst.com/schemas/narrative-risk/stakeholder-intelligence/{VERSION}",
        "catalyst_canvas_stakeholder_handoff": f"https://sustainablecatalyst.com/schemas/narrative-risk/handoff/catalyst-canvas-stakeholders/{VERSION}",
        "comparison_set": f"https://sustainablecatalyst.com/schemas/narrative-risk/comparison-set/{VERSION}",
        "comparative_evidence_matrix": f"https://sustainablecatalyst.com/schemas/narrative-risk/comparative-evidence-matrix/{VERSION}",
        "scenario": f"https://sustainablecatalyst.com/schemas/narrative-risk/scenario/{VERSION}",
        "scenario_result": f"https://sustainablecatalyst.com/schemas/narrative-risk/scenario-result/{VERSION}",
        "sensitivity_analysis": f"https://sustainablecatalyst.com/schemas/narrative-risk/sensitivity-analysis/{VERSION}",
        "comparative_portfolio": f"https://sustainablecatalyst.com/schemas/narrative-risk/comparative-portfolio/{VERSION}",
        "decision_studio_handoff": f"https://sustainablecatalyst.com/schemas/narrative-risk/decision-studio-handoff/{VERSION}",
        "briefing": f"https://sustainablecatalyst.com/schemas/narrative-risk/briefing/{VERSION}",
        "publication_package": f"https://sustainablecatalyst.com/schemas/narrative-risk/publication-package/{VERSION}",
        "public_embed": f"https://sustainablecatalyst.com/schemas/narrative-risk/public-embed/{VERSION}",
        "api_key": f"https://sustainablecatalyst.com/schemas/narrative-risk/api-key/{VERSION}",
        "platform_handoff": f"https://sustainablecatalyst.com/schemas/narrative-risk/platform-handoff/{VERSION}",
        "security_report": f"https://sustainablecatalyst.com/schemas/narrative-risk/security-report/{VERSION}",
        "privacy_policy": f"https://sustainablecatalyst.com/schemas/narrative-risk/privacy-policy/{VERSION}",
        "retention_assessment": f"https://sustainablecatalyst.com/schemas/narrative-risk/retention-assessment/{VERSION}",
        "backup_manifest": f"https://sustainablecatalyst.com/schemas/narrative-risk/backup-manifest/{VERSION}",
        "accessibility_report": f"https://sustainablecatalyst.com/schemas/narrative-risk/accessibility-report/{VERSION}",
        "performance_report": f"https://sustainablecatalyst.com/schemas/narrative-risk/performance-report/{VERSION}",
        "production_readiness": f"https://sustainablecatalyst.com/schemas/narrative-risk/production-readiness/{VERSION}",
        "platform_profile": f"https://sustainablecatalyst.com/schemas/narrative-risk/platform-profile/{VERSION}",
        "platform_event": f"https://sustainablecatalyst.com/schemas/narrative-risk/platform-event/{VERSION}",
        "integration_route": f"https://sustainablecatalyst.com/schemas/narrative-risk/integration-route/{VERSION}",
        "connected_dossier": f"https://sustainablecatalyst.com/schemas/narrative-risk/connected-dossier/{VERSION}",
        "institutional_workspace": f"https://sustainablecatalyst.com/schemas/narrative-risk/institutional-workspace/{VERSION}",
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
    migration_sources = ["1.0.1", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0", "1.7.0", "1.8.0", "1.9.0", "1.10.0"]
    if contract.get("compatibility", {}).get("migrates_from") != migration_sources or manifest.get("migration_sources") != migration_sources:
        fail("legacy migration declarations are incomplete")
    if manifest.get("database") != "sqlite3" or "sqlite3" not in manifest.get("runtime_contracts", []):
        fail("SQLite runtime contract missing")
    if manifest.get("workspace_shortcodes") != ["[catalyst_narrative_risk_demo]", "[catalyst_narrative_risk_workspace]", "[catalyst_narrative_risk_publication_workspace]", "[catalyst_narrative_risk_public_brief]", "[catalyst_narrative_risk_readiness]", "[catalyst_narrative_risk_platform]"]:
        fail("workspace shortcode manifest is incomplete")

    # The connected platform is additive and must not silently change the v1.10 analytical, governance, monitoring, stakeholder, comparative, publication, or hardening engine.
    for key in ("algorithm", "weights", "components", "interpretation", "ledger_policy", "narrative_map_policy", "governance_policy", "monitoring_policy", "stakeholder_policy", "comparative_policy", "publication_policy", "hardening_policy"):
        previous = json.loads(json.dumps(previous_method[key]))
        current = json.loads(json.dumps(method[key]))
        if key.endswith("policy"):
            previous["policy_version"] = VERSION
            current["policy_version"] = VERSION
        if previous != current:
            fail(f"v2.0.0 unexpectedly changed inherited analytical or governance section: {key}")
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

    stakeholder_policy = method.get("stakeholder_policy", {})
    if stakeholder_policy.get("boundary") != "Stakeholder intelligence documents observable actors, relationships, incentives, pressures, disclosures, and consequences. It does not infer undisclosed motives, certify conflicts, or silently change the analytical score.":
        fail("stakeholder methodological boundary mismatch")
    if set(vocabs["vocabularies"]["stakeholder_actor_type"]["values"]) != ACTOR_TYPES:
        fail("stakeholder actor vocabulary mismatch")
    if set(vocabs["vocabularies"]["stakeholder_relationship_type"]["values"]) != RELATIONSHIP_TYPES:
        fail("stakeholder relationship vocabulary mismatch")
    if set(vocabs["vocabularies"]["incentive_type"]["values"]) != INCENTIVE_TYPES:
        fail("stakeholder incentive vocabulary mismatch")
    if set(vocabs["vocabularies"]["pressure_type"]["values"]) != PRESSURE_TYPES:
        fail("stakeholder pressure vocabulary mismatch")
    if set(vocabs["vocabularies"]["stakeholder_impact_type"]["values"]) != IMPACT_TYPES:
        fail("stakeholder consequence vocabulary mismatch")

    comparative_policy = method.get("comparative_policy", {})
    if comparative_policy.get("boundary") != "Comparative analysis evaluates explicit records, frames, assumptions, and scenarios. It does not certify truth, infer an optimal narrative, or silently change canonical analytical scores.":
        fail("comparative methodological boundary mismatch")
    if set(comparative_policy.get("scenario_types", [])) != SCENARIO_TYPES:
        fail("comparative scenario vocabulary mismatch")
    if set(comparative_policy.get("sensitivity_dimensions", [])) != set(SENSITIVITY_DIMENSIONS):
        fail("comparative sensitivity dimensions mismatch")
    if set(vocabs["vocabularies"]["comparison_status"]["values"]) != COMPARISON_STATUSES:
        fail("comparison status vocabulary mismatch")
    if set(vocabs["vocabularies"]["comparison_mode"]["values"]) != COMPARISON_MODES:
        fail("comparison mode vocabulary mismatch")
    if set(vocabs["vocabularies"]["scenario_status"]["values"]) != SCENARIO_STATUSES:
        fail("scenario status vocabulary mismatch")

    publication_policy = method.get("publication_policy", {})
    if set(publication_policy.get("formats", [])) != FORMATS:
        fail("publication format policy mismatch")
    if set(schemas["briefing"]["properties"]["audience"]["enum"]) != AUDIENCES:
        fail("briefing audience schema mismatch")
    if set(schemas["briefing"]["properties"]["classification"]["enum"]) != CLASSIFICATIONS:
        fail("briefing classification schema mismatch")
    if set(schemas["publication_package"]["properties"]["status"]["enum"]) != PACKAGE_STATUSES:
        fail("publication package status schema mismatch")
    if set(schemas["public_embed"]["properties"]["status"]["enum"]) != EMBED_STATUSES:
        fail("public embed status schema mismatch")
    if set(schemas["api_key"]["properties"]["scopes"]["items"]["enum"]) != API_SCOPES:
        fail("API scope schema mismatch")
    if set(schemas["platform_handoff"]["properties"]["target"]["enum"]) != PLATFORM_TARGETS:
        fail("platform handoff target schema mismatch")

    hardening_policy = method.get("hardening_policy", {})
    if hardening_policy.get("boundary") != "Production-readiness reports evaluate declared controls and local artifacts. They do not certify security, privacy compliance, accessibility conformance, disaster recovery, or legal sufficiency.":
        fail("production-hardening methodological boundary mismatch")
    if hardening_policy.get("minimum_admin_token_characters") != 32:
        fail("administrator token policy mismatch")
    if hardening_policy.get("maximum_request_bytes") != 2097152:
        fail("request-size policy mismatch")
    if set(hardening_policy.get("privacy_deletion_modes", [])) != {"archive_and_tombstone", "anonymize_then_archive", "legal_hold_only"}:
        fail("privacy deletion-mode policy mismatch")

    connected_policy = method.get("connected_platform_policy", {})
    if set(connected_policy.get("modules", [])) != set(MODULES):
        fail("connected module registry and method policy differ")
    if set(connected_policy.get("event_types", [])) != set(EVENT_TYPES):
        fail("connected platform event vocabulary mismatch")
    if set(connected_policy.get("route_statuses", [])) != set(ROUTE_STATUSES):
        fail("connected integration-route status mismatch")
    if connected_policy.get("boundary") != "Connected dossiers and institutional rollups summarize explicit records and routes. They do not alter risk scores, create approval, infer truth, or bypass source-module permissions.":
        fail("connected-platform methodological boundary mismatch")

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
    if not all(bundle_report[key] for key in ("bundle_sha256_match", "all_revision_hashes_match", "all_case_ids_match", "governance_case_ids_match", "monitoring_case_ids_match", "all_snapshot_hashes_match", "all_comparison_hashes_match", "stakeholder_case_ids_match", "stakeholder_intelligence_hash_match", "comparative_case_ids_match", "comparative_hashes_match", "publication_case_ids_match", "publication_hashes_match")):
        fail(f"sample workspace bundle verification failed: {bundle_report}")
    if not sample_bundle.get("retention_assessments"):
        fail("sample workspace bundle must exercise privacy-retention assessment records")
    if sample_bundle["retention_assessments"][0].get("assessment_version") != VERSION:
        fail("sample retention assessment version mismatch")
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
    if not all(sample_bundle[key] for key in ("stakeholder_actors", "stakeholder_relationships", "stakeholder_incentives", "stakeholder_pressures", "stakeholder_consequences")):
        fail("sample workspace bundle must exercise the complete stakeholder graph")
    if sample_bundle["stakeholder_intelligence"]["suggested_stakeholder_pressure"] != "high":
        fail("sample stakeholder intelligence must exercise high pressure")
    if not sample_bundle["catalyst_canvas_handoffs"]:
        fail("sample workspace bundle must preserve a Catalyst Canvas handoff")
    if not sample_bundle["comparison_sets"] or not sample_bundle["comparative_evidence_matrices"]:
        fail("sample workspace bundle must exercise comparative narratives and evidence matrices")
    if len(sample_bundle["scenarios"]) < 3 or len(sample_bundle["scenario_results"]) < 3:
        fail("sample workspace bundle must exercise multiple evaluated scenarios")
    if not sample_bundle["sensitivity_analyses"] or not sample_bundle["decision_studio_handoffs"]:
        fail("sample workspace bundle must exercise sensitivity analysis and Decision Studio handoff")
    if sample_bundle["comparative_portfolio"]["comparison_count"] < 1:
        fail("sample comparative portfolio is incomplete")
    if not sample_bundle["publication_briefings"] or not sample_bundle["publication_packages"]:
        fail("sample workspace bundle must exercise publication briefings and packages")
    if sample_bundle["publication_packages"][0]["status"] != "published" or len(sample_bundle["publication_packages"][0]["artifacts"]) != 6:
        fail("sample publication package must be published with six formats")
    if not sample_bundle["public_embeds"] or len(sample_bundle["platform_handoffs"]) < 3:
        fail("sample workspace bundle must exercise public embeds and platform handoffs")
    if not sample_bundle.get("connected_dossiers") or not sample_bundle.get("platform_events") or not sample_bundle.get("integration_routes"):
        fail("sample workspace bundle must exercise connected dossiers, platform events, and integration routes")
    if len(sample_bundle["platform_events"]) < 2 or len(sample_bundle["integration_routes"]) < 2:
        fail("sample connected platform fixtures are incomplete")
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
        "1.4.0": migrate_v1_4_0_record, "1.5.0": migrate_v1_5_0_record, "1.6.0": migrate_v1_6_0_record,
        "1.7.0": migrate_v1_7_0_record, "1.8.0": migrate_v1_8_0_record, "1.9.0": migrate_v1_9_0_record, "1.10.0": migrate_v1_10_0_record,
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
    canvas_handoff = load_json(ROOT / "data/handoffs/catalyst_canvas_stakeholder_handoff.json")
    validate_canvas_handoff(canvas_handoff)
    if canvas_handoff["handoff_version"] != VERSION or len(canvas_handoff["stakeholders"]) < 3:
        fail("Catalyst Canvas stakeholder handoff is incomplete")

    plugin_version = re.search(r"^ \* Version:\s*(\S+)", plugin, re.MULTILINE)
    if not plugin_version or plugin_version.group(1) != VERSION:
        fail("WordPress plugin header version mismatch")
    for token in ["catalyst_narrative_risk_demo", "catalyst_narrative_risk_workspace", "catalyst_narrative_risk_publication_workspace", "catalyst_narrative_risk_public_brief", "catalyst_narrative_risk_readiness", "catalyst_narrative_risk_platform", "cnrisk-map-js", "cnrisk-publication-js", "narrative-risk-map.js", "array('cnrisk-method-js', 'cnrisk-map-js')"]:
        if token not in plugin:
            fail(f"WordPress narrative-map token missing: {token}")
    for token in ["narrative_map_json", "data-cnrisk-map-summary", "narrative_map"]:
        if token not in plugin + demo_js:
            fail(f"WordPress map-interface token missing: {token}")
    for token in ["catalyst_narrative_risk_case_bundle", "localStorage", "revision_added", "bundle_sha256", "governance_workflow", "review_assignments", "governance_decisions", "publication_allowed", "monitoring_snapshots", "watchlists", "monitoring_alerts", "material_change", "data-cnrisk-run-watch", "stakeholder_actors", "stakeholder_relationships", "stakeholder_incentives", "stakeholder_pressures", "stakeholder_consequences", "stakeholder_intelligence", "data-cnrisk-add-actor", "data-cnrisk-add-pressure", "comparison_sets", "comparative_evidence_matrices", "scenarios", "scenario_results", "sensitivity_analyses", "comparative_portfolio", "decision_studio_handoffs", "data-cnrisk-create-comparison", "data-cnrisk-add-scenario", "data-cnrisk-run-sensitivity", "data-cnrisk-decision-studio-handoff", "publication_briefings", "publication_packages", "public_embeds", "platform_handoffs", "retention_assessments", "v2.0.0"]:
        if token not in workspace_js:
            fail(f"WordPress workspace behavior token missing: {token}")

    for token in ["data-cnrisk-publication", "data-cnrisk-publication-preview", "data-cnrisk-download-format", "contract_version", "public_safe"]:
        if token not in plugin + publication_js:
            fail(f"WordPress publication token missing: {token}")

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
        ROOT / "outputs/sample_public_brief.json", ROOT / "outputs/sample_public_brief.md",
        ROOT / "outputs/sample_public_brief.html", ROOT / "outputs/sample_public_brief.pdf",
        ROOT / "outputs/sample_public_brief.csv", ROOT / "outputs/sample_public_brief.jsonld",
        ROOT / "outputs/sample_platform_profile.json", ROOT / "outputs/sample_connected_dossier.json",
        ROOT / "outputs/sample_institutional_workspace.json",
    ]:
        if output.stat().st_size == 0:
            fail(f"empty sample output: {output.relative_to(ROOT)}")

    print("Catalyst Narrative Risk v2.0.0 release contract passed.")
    print(
        f"Version checks: {len(versions)}; identifier checks: {len(identifiers)}; "
        f"parity fixtures: {len(fixtures['valid'])} valid, {len(fixtures['invalid'])} invalid; "
        "six-layer reproduction, connected dossiers, and workspace bundle round trip: exact."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
