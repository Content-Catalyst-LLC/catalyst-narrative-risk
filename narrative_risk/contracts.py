"""Contract, schema, canonicalization, and hashing utilities for v1.9.0."""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.9.0"
CONTRACT_PATH = ROOT / "contracts" / "narrative-risk-contract.v1.9.0.json"
VOCABULARIES_PATH = ROOT / "contracts" / "controlled-vocabularies.v1.9.0.json"
METHOD_PATH = ROOT / "methods" / "transparent-heuristic.v1.9.0.json"
INPUT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_input.schema.json"
LEDGER_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_evidence_ledger.schema.json"
NARRATIVE_MAP_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_narrative_map.schema.json"
METHOD_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_method_snapshot.schema.json"
RECORD_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_record.schema.json"
KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH = ROOT / "schemas" / "knowledge_library_source_handoff.schema.json"
CATALYST_DATA_HANDOFF_SCHEMA_PATH = ROOT / "schemas" / "catalyst_data_source_handoff.schema.json"
CASE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_case.schema.json"
REVISION_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_revision.schema.json"
REVIEW_EVENT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_review_event.schema.json"
SAVED_VIEW_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_saved_view.schema.json"
WORKSPACE_BUNDLE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_workspace_bundle.schema.json"
REVIEW_ASSIGNMENT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_review_assignment.schema.json"
GOVERNANCE_WORKFLOW_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_governance_workflow.schema.json"
GOVERNANCE_DECISION_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_governance_decision.schema.json"
REVIEW_TEMPLATE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_review_template.schema.json"
MONITORING_SNAPSHOT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_monitoring_snapshot.schema.json"
MONITORING_COMPARISON_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_monitoring_comparison.schema.json"
WATCHLIST_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_watchlist.schema.json"
MONITORING_ALERT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_monitoring_alert.schema.json"
SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH = ROOT / "schemas" / "site_intelligence_monitoring_handoff.schema.json"
STAKEHOLDER_ACTOR_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_stakeholder_actor.schema.json"
STAKEHOLDER_RELATIONSHIP_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_stakeholder_relationship.schema.json"
STAKEHOLDER_INCENTIVE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_stakeholder_incentive.schema.json"
STAKEHOLDER_PRESSURE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_stakeholder_pressure.schema.json"
STAKEHOLDER_CONSEQUENCE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_stakeholder_consequence.schema.json"
STAKEHOLDER_INTELLIGENCE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_stakeholder_intelligence.schema.json"
CATALYST_CANVAS_STAKEHOLDER_HANDOFF_SCHEMA_PATH = ROOT / "schemas" / "catalyst_canvas_stakeholder_handoff.schema.json"
COMPARISON_SET_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_comparison_set.schema.json"
COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_comparative_evidence_matrix.schema.json"
SCENARIO_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_scenario.schema.json"
SCENARIO_RESULT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_scenario_result.schema.json"
SENSITIVITY_ANALYSIS_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_sensitivity_analysis.schema.json"
COMPARATIVE_PORTFOLIO_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_comparative_portfolio.schema.json"
DECISION_STUDIO_HANDOFF_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_decision_studio_handoff.schema.json"
BRIEFING_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_briefing.schema.json"
PUBLICATION_PACKAGE_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_publication_package.schema.json"
PUBLIC_EMBED_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_public_embed.schema.json"
API_KEY_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_api_key.schema.json"
PLATFORM_HANDOFF_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_platform_handoff.schema.json"
LEGACY_V160_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.6.0.schema.json"
LEGACY_V160_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.6.0.schema.json"
LEGACY_V160_NARRATIVE_MAP_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_narrative_map.v1.6.0.schema.json"
LEGACY_V160_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.6.0.schema.json"
LEGACY_V160_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.6.0.schema.json"
LEGACY_V170_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.7.0.schema.json"
LEGACY_V170_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.7.0.schema.json"
LEGACY_V170_NARRATIVE_MAP_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_narrative_map.v1.7.0.schema.json"
LEGACY_V170_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.7.0.schema.json"
LEGACY_V170_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.7.0.schema.json"
LEGACY_V180_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.8.0.schema.json"
LEGACY_V180_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.8.0.schema.json"
LEGACY_V180_NARRATIVE_MAP_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_narrative_map.v1.8.0.schema.json"
LEGACY_V180_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.8.0.schema.json"
LEGACY_V180_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.8.0.schema.json"
LEGACY_V101_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.0.1.schema.json"
LEGACY_V110_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.1.0.schema.json"
LEGACY_V110_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.1.0.schema.json"
LEGACY_V110_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.1.0.schema.json"
LEGACY_V120_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.2.0.schema.json"
LEGACY_V120_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.2.0.schema.json"
LEGACY_V120_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.2.0.schema.json"
LEGACY_V120_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.2.0.schema.json"
LEGACY_V130_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.3.0.schema.json"
LEGACY_V130_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.3.0.schema.json"
LEGACY_V130_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.3.0.schema.json"
LEGACY_V130_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.3.0.schema.json"
LEGACY_V140_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.4.0.schema.json"
LEGACY_V140_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.4.0.schema.json"
LEGACY_V140_NARRATIVE_MAP_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_narrative_map.v1.4.0.schema.json"
LEGACY_V140_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.4.0.schema.json"
LEGACY_V140_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.4.0.schema.json"
LEGACY_V150_INPUT_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_input.v1.5.0.schema.json"
LEGACY_V150_LEDGER_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_evidence_ledger.v1.5.0.schema.json"
LEGACY_V150_NARRATIVE_MAP_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_narrative_map.v1.5.0.schema.json"
LEGACY_V150_METHOD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_method_snapshot.v1.5.0.schema.json"
LEGACY_V150_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.5.0.schema.json"
# Backwards-compatible alias retained for integrations written against v1.1.0.
LEGACY_RECORD_SCHEMA_PATH = LEGACY_V101_RECORD_SCHEMA_PATH


@lru_cache(maxsize=None)
def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def contract_definition() -> dict[str, Any]:
    return _clone(load_json(CONTRACT_PATH))


def controlled_vocabularies() -> dict[str, Any]:
    return _clone(load_json(VOCABULARIES_PATH))


def current_method_snapshot() -> dict[str, Any]:
    return _clone(load_json(METHOD_PATH))


def _canonical_value(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    return value


def canonical_json(value: Any) -> str:
    """Return the cross-runtime canonical JSON representation used for digests."""
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _registry():
    try:
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("referencing is required to validate narrative-risk schemas") from exc

    schema_paths = [
        INPUT_SCHEMA_PATH,
        LEDGER_SCHEMA_PATH,
        NARRATIVE_MAP_SCHEMA_PATH,
        METHOD_SCHEMA_PATH,
        RECORD_SCHEMA_PATH,
        KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH,
        CATALYST_DATA_HANDOFF_SCHEMA_PATH,
        CASE_SCHEMA_PATH,
        REVISION_SCHEMA_PATH,
        REVIEW_EVENT_SCHEMA_PATH,
        SAVED_VIEW_SCHEMA_PATH,
        WORKSPACE_BUNDLE_SCHEMA_PATH,
        REVIEW_ASSIGNMENT_SCHEMA_PATH, GOVERNANCE_WORKFLOW_SCHEMA_PATH,
        GOVERNANCE_DECISION_SCHEMA_PATH, REVIEW_TEMPLATE_SCHEMA_PATH,
        MONITORING_SNAPSHOT_SCHEMA_PATH, MONITORING_COMPARISON_SCHEMA_PATH,
        WATCHLIST_SCHEMA_PATH, MONITORING_ALERT_SCHEMA_PATH, SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH,
        STAKEHOLDER_ACTOR_SCHEMA_PATH, STAKEHOLDER_RELATIONSHIP_SCHEMA_PATH,
        STAKEHOLDER_INCENTIVE_SCHEMA_PATH, STAKEHOLDER_PRESSURE_SCHEMA_PATH,
        STAKEHOLDER_CONSEQUENCE_SCHEMA_PATH, STAKEHOLDER_INTELLIGENCE_SCHEMA_PATH,
        CATALYST_CANVAS_STAKEHOLDER_HANDOFF_SCHEMA_PATH,
        COMPARISON_SET_SCHEMA_PATH, COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH,
        SCENARIO_SCHEMA_PATH, SCENARIO_RESULT_SCHEMA_PATH, SENSITIVITY_ANALYSIS_SCHEMA_PATH,
        COMPARATIVE_PORTFOLIO_SCHEMA_PATH, DECISION_STUDIO_HANDOFF_SCHEMA_PATH,
        BRIEFING_SCHEMA_PATH, PUBLICATION_PACKAGE_SCHEMA_PATH, PUBLIC_EMBED_SCHEMA_PATH,
        API_KEY_SCHEMA_PATH, PLATFORM_HANDOFF_SCHEMA_PATH,
        LEGACY_V101_RECORD_SCHEMA_PATH,
        LEGACY_V110_INPUT_SCHEMA_PATH,
        LEGACY_V110_METHOD_SCHEMA_PATH,
        LEGACY_V110_RECORD_SCHEMA_PATH,
        LEGACY_V120_INPUT_SCHEMA_PATH,
        LEGACY_V120_LEDGER_SCHEMA_PATH,
        LEGACY_V120_METHOD_SCHEMA_PATH,
        LEGACY_V120_RECORD_SCHEMA_PATH,
        LEGACY_V130_INPUT_SCHEMA_PATH,
        LEGACY_V130_LEDGER_SCHEMA_PATH,
        LEGACY_V130_METHOD_SCHEMA_PATH,
        LEGACY_V130_RECORD_SCHEMA_PATH,
        LEGACY_V140_INPUT_SCHEMA_PATH, LEGACY_V140_LEDGER_SCHEMA_PATH,
        LEGACY_V140_NARRATIVE_MAP_SCHEMA_PATH, LEGACY_V140_METHOD_SCHEMA_PATH,
        LEGACY_V140_RECORD_SCHEMA_PATH,
        LEGACY_V150_INPUT_SCHEMA_PATH, LEGACY_V150_LEDGER_SCHEMA_PATH,
        LEGACY_V150_NARRATIVE_MAP_SCHEMA_PATH, LEGACY_V150_METHOD_SCHEMA_PATH,
        LEGACY_V150_RECORD_SCHEMA_PATH,
        LEGACY_V160_INPUT_SCHEMA_PATH, LEGACY_V160_LEDGER_SCHEMA_PATH,
        LEGACY_V160_NARRATIVE_MAP_SCHEMA_PATH, LEGACY_V160_METHOD_SCHEMA_PATH,
        LEGACY_V160_RECORD_SCHEMA_PATH,
        LEGACY_V170_INPUT_SCHEMA_PATH, LEGACY_V170_LEDGER_SCHEMA_PATH,
        LEGACY_V170_NARRATIVE_MAP_SCHEMA_PATH, LEGACY_V170_METHOD_SCHEMA_PATH,
        LEGACY_V170_RECORD_SCHEMA_PATH,
        LEGACY_V180_INPUT_SCHEMA_PATH, LEGACY_V180_LEDGER_SCHEMA_PATH,
        LEGACY_V180_NARRATIVE_MAP_SCHEMA_PATH, LEGACY_V180_METHOD_SCHEMA_PATH,
        LEGACY_V180_RECORD_SCHEMA_PATH,
    ]
    registry = Registry()
    for path in schema_paths:
        schema = load_json(path)
        schema_id = schema.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return registry


def validate_against_schema(value: Mapping[str, Any], schema_path: Path) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("jsonschema is required to validate narrative-risk records") from exc

    schema = load_json(schema_path)
    validator = Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    validator.validate(dict(value))
