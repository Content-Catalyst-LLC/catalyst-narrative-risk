"""Connected institutional platform contracts for Catalyst Narrative Risk v2.0.0."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID, uuid4

from .contracts import (
    CONNECTED_DOSSIER_SCHEMA_PATH,
    INSTITUTIONAL_WORKSPACE_SCHEMA_PATH,
    INTEGRATION_ROUTE_SCHEMA_PATH,
    PLATFORM_EVENT_SCHEMA_PATH,
    PLATFORM_PROFILE_SCHEMA_PATH,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError

VERSION = "2.0.0"
MODULES = (
    "narrative_risk",
    "knowledge_library",
    "catalyst_data",
    "site_intelligence",
    "catalyst_canvas",
    "decision_studio",
    "research_librarian",
    "workbench",
    "catalyst_analytics",
    "publication_api",
)
EVENT_TYPES = (
    "claim_created", "evidence_added", "record_revised", "review_decided",
    "monitoring_signal", "stakeholder_changed", "scenario_evaluated",
    "publication_changed", "handoff_created", "retention_changed", "custom",
)
ROUTE_STATUSES = ("queued", "delivered", "acknowledged", "failed")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_datetime(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string") from exc
    if parsed.tzinfo is None:
        raise NarrativeRiskValidationError(f"{field} must include a timezone")
    return value


def _urn(value: str | None, field: str) -> str:
    if value is None:
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except (ValueError, AttributeError) as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def _text(value: Any, field: str, *, required: bool = False, maximum: int = 500) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    if len(cleaned) > maximum:
        raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum} characters")
    return cleaned


def _schema(label: str, value: Mapping[str, Any], path) -> None:
    try:
        validate_against_schema(value, path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


def _hashed(payload: dict[str, Any], field: str) -> dict[str, Any]:
    payload[field] = sha256_digest(payload)
    return payload


def build_platform_profile(
    *,
    manifest: Mapping[str, Any],
    contract: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    timestamp = _validate_datetime(generated_at, "generated_at") if generated_at else _iso_now()
    module_details = [
        {
            "module": name,
            "status": "connected",
            "role": {
                "narrative_risk": "claims, evidence, governance, monitoring, and publication authority",
                "knowledge_library": "source discovery and publication archive",
                "catalyst_data": "dataset provenance and observations",
                "site_intelligence": "external monitoring signals",
                "catalyst_canvas": "stakeholder and journey context",
                "decision_studio": "scenario and decision handoff",
                "research_librarian": "guided research routing",
                "workbench": "calculation and modeling handoff",
                "catalyst_analytics": "statistical analysis handoff",
                "publication_api": "public-safe distribution and embeds",
            }[name],
        }
        for name in MODULES
    ]
    profile = {
        "profile_type": "catalyst-narrative-risk-platform-profile",
        "profile_version": VERSION,
        "generated_at": timestamp,
        "platform_name": manifest.get("name", "Catalyst Narrative Risk"),
        "release_name": manifest.get("release_name", "Connected Narrative Risk and Claims Governance Platform"),
        "modules": module_details,
        "capabilities": sorted(set(str(item) for item in manifest.get("capabilities", []))),
        "data_contracts": sorted(
            value for key, value in contract.items()
            if key.endswith("_schema_id") and isinstance(value, str)
        ),
        "runtime_contracts": list(manifest.get("runtime_contracts", [])),
        "migration_sources": list(manifest.get("migration_sources", [])),
    }
    _hashed(profile, "profile_sha256")
    _schema("platform profile", profile, PLATFORM_PROFILE_SCHEMA_PATH)
    return profile


def normalize_platform_event(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("platform event must be a JSON object")
    source_module = _text(payload.get("source_module"), "source_module", required=True, maximum=80)
    if source_module not in MODULES:
        raise NarrativeRiskValidationError("source_module is not a connected Catalyst module")
    event_type = _text(payload.get("event_type"), "event_type", required=True, maximum=80)
    if event_type not in EVENT_TYPES:
        raise NarrativeRiskValidationError("event_type is not supported")
    targets = payload.get("target_modules", [])
    if not isinstance(targets, Sequence) or isinstance(targets, (str, bytes)):
        raise NarrativeRiskValidationError("target_modules must be an array")
    target_modules: list[str] = []
    for item in targets:
        target = _text(item, "target_modules[]", required=True, maximum=80)
        if target not in MODULES:
            raise NarrativeRiskValidationError("target_modules contains an unknown Catalyst module")
        if target not in target_modules:
            target_modules.append(target)
    case_id = payload.get("case_id")
    if case_id is not None:
        case_id = _urn(case_id, "case_id")
    body = payload.get("payload", {})
    if not isinstance(body, Mapping):
        raise NarrativeRiskValidationError("payload must be a JSON object")
    event = {
        "event_id": _urn(payload.get("event_id"), "event_id"),
        "event_version": VERSION,
        "case_id": case_id,
        "source_module": source_module,
        "target_modules": target_modules,
        "event_type": event_type,
        "occurred_at": _validate_datetime(payload.get("occurred_at") or _iso_now(), "occurred_at"),
        "idempotency_key": _text(payload.get("idempotency_key"), "idempotency_key", required=True, maximum=200),
        "payload": deepcopy(dict(body)),
    }
    _hashed(event, "event_sha256")
    _schema("platform event", event, PLATFORM_EVENT_SCHEMA_PATH)
    return event


def build_integration_route(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("integration route must be a JSON object")
    source = _text(payload.get("source_module"), "source_module", required=True, maximum=80)
    target = _text(payload.get("target_module"), "target_module", required=True, maximum=80)
    if source not in MODULES or target not in MODULES or source == target:
        raise NarrativeRiskValidationError("source_module and target_module must be different connected modules")
    status = _text(payload.get("status") or "queued", "status", required=True, maximum=40)
    if status not in ROUTE_STATUSES:
        raise NarrativeRiskValidationError("status is not supported")
    route = {
        "route_id": _urn(payload.get("route_id"), "route_id"),
        "route_version": VERSION,
        "case_id": _urn(payload.get("case_id"), "case_id"),
        "source_module": source,
        "target_module": target,
        "artifact_type": _text(payload.get("artifact_type"), "artifact_type", required=True, maximum=120),
        "artifact_id": _text(payload.get("artifact_id"), "artifact_id", required=True, maximum=300),
        "status": status,
        "created_at": _validate_datetime(payload.get("created_at") or _iso_now(), "created_at"),
        "external_reference": _text(payload.get("external_reference"), "external_reference", maximum=500) or None,
        "payload_sha256": _text(payload.get("payload_sha256"), "payload_sha256", required=True, maximum=64).lower(),
    }
    _hashed(route, "route_sha256")
    _schema("integration route", route, INTEGRATION_ROUTE_SCHEMA_PATH)
    return route


def build_connected_dossier(
    *,
    case: Mapping[str, Any],
    latest_revision: Mapping[str, Any] | None,
    governance: Mapping[str, Any] | None,
    alerts: Sequence[Mapping[str, Any]],
    stakeholder_intelligence: Mapping[str, Any],
    comparative_portfolio: Mapping[str, Any],
    publication_packages: Sequence[Mapping[str, Any]],
    platform_handoffs: Sequence[Mapping[str, Any]],
    retention_assessments: Sequence[Mapping[str, Any]],
    platform_events: Sequence[Mapping[str, Any]],
    integration_routes: Sequence[Mapping[str, Any]],
    generated_at: str | None = None,
    dossier_id: str | None = None,
) -> dict[str, Any]:
    timestamp = _validate_datetime(generated_at, "generated_at") if generated_at else _iso_now()
    record = latest_revision.get("record") if latest_revision else None
    open_alerts = [item for item in alerts if item.get("status") == "open"]
    latest_retention = retention_assessments[-1] if retention_assessments else None
    dossier = {
        "dossier_type": "catalyst-narrative-risk-connected-dossier",
        "dossier_version": VERSION,
        "dossier_id": _urn(dossier_id, "dossier_id"),
        "case_id": case["case_id"],
        "generated_at": timestamp,
        "case_summary": {
            "title": case["title"], "status": case["status"], "priority": case["priority"],
            "organization_id": case.get("organization_id"), "project_id": case.get("project_id"),
            "current_revision": case["current_revision"], "tags": list(case.get("tags", [])),
        },
        "analytical_summary": {
            "record_id": record.get("identifiers", {}).get("record_id") if record else None,
            "risk_score": record.get("calculations", {}).get("risk_score") if record else None,
            "risk_level": record.get("interpretation", {}).get("risk_level") if record else None,
            "claim_count": len(record.get("evidence_ledger", {}).get("claims", [])) if record else 0,
            "source_count": len(record.get("evidence_ledger", {}).get("sources", [])) if record else 0,
            "narrative_node_count": len(record.get("narrative_map", {}).get("nodes", [])) if record else 0,
        },
        "governance_summary": {
            "workflow_status": governance.get("status") if governance else None,
            "current_stage": governance.get("current_stage") if governance else None,
            "final_disposition": governance.get("final_disposition") if governance else None,
            "publication_allowed": bool(governance.get("publication_allowed")) if governance else False,
            "reassessment_at": governance.get("reassessment_at") if governance else None,
        },
        "monitoring_summary": {
            "open_alert_count": len(open_alerts),
            "critical_alert_count": sum(1 for item in open_alerts if item.get("severity") == "critical"),
            "latest_alert_at": max((item.get("created_at") for item in alerts), default=None),
        },
        "stakeholder_summary": {
            "actor_count": stakeholder_intelligence.get("counts", {}).get("actors", 0),
            "pressure_count": stakeholder_intelligence.get("counts", {}).get("pressures", 0),
            "suggested_pressure": stakeholder_intelligence.get("suggested_stakeholder_pressure"),
            "flag_count": len(stakeholder_intelligence.get("flags", [])),
        },
        "comparative_summary": {
            "comparison_count": comparative_portfolio.get("counts", {}).get("comparison_sets", 0),
            "scenario_count": comparative_portfolio.get("counts", {}).get("scenarios", 0),
            "evaluated_scenario_count": comparative_portfolio.get("counts", {}).get("scenario_results", 0),
        },
        "publication_summary": {
            "package_count": len(publication_packages),
            "published_count": sum(1 for item in publication_packages if item.get("status") == "published"),
            "handoff_count": len(platform_handoffs),
        },
        "privacy_summary": {
            "assessment_count": len(retention_assessments),
            "latest_status": latest_retention.get("status") if latest_retention else None,
            "legal_hold": bool(latest_retention.get("legal_hold")) if latest_retention else False,
        },
        "module_links": [
            {"module": module, "event_count": sum(1 for item in platform_events if item.get("source_module") == module),
             "outbound_route_count": sum(1 for item in integration_routes if item.get("source_module") == module),
             "inbound_route_count": sum(1 for item in integration_routes if item.get("target_module") == module)}
            for module in MODULES
        ],
    }
    _hashed(dossier, "dossier_sha256")
    _schema("connected dossier", dossier, CONNECTED_DOSSIER_SCHEMA_PATH)
    return dossier


def build_institutional_workspace(
    *,
    organization_id: str,
    cases: Sequence[Mapping[str, Any]],
    dossiers: Sequence[Mapping[str, Any]],
    platform_events: Sequence[Mapping[str, Any]],
    integration_routes: Sequence[Mapping[str, Any]],
    generated_at: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    org = _text(organization_id, "organization_id", required=True, maximum=200)
    timestamp = _validate_datetime(generated_at, "generated_at") if generated_at else _iso_now()
    status_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for case in cases:
        status_counts[case["status"]] = status_counts.get(case["status"], 0) + 1
        priority_counts[case["priority"]] = priority_counts.get(case["priority"], 0) + 1
    workspace = {
        "workspace_type": "catalyst-narrative-risk-institutional-workspace",
        "workspace_version": VERSION,
        "workspace_id": _urn(workspace_id, "workspace_id"),
        "organization_id": org,
        "generated_at": timestamp,
        "case_count": len(cases),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "open_monitoring_alerts": sum(int(case.get("open_alert_count", 0)) for case in cases),
        "pending_reviews": sum(int(case.get("assignment_count", 0)) for case in cases if case.get("workflow_status") not in {None, "completed"}),
        "publication_ready_cases": sum(1 for case in cases if case.get("publication_allowed")),
        "connected_dossier_ids": [item["dossier_id"] for item in dossiers],
        "module_connections": {
            module: {
                "events": sum(1 for item in platform_events if item.get("source_module") == module),
                "outbound_routes": sum(1 for item in integration_routes if item.get("source_module") == module),
                "inbound_routes": sum(1 for item in integration_routes if item.get("target_module") == module),
            }
            for module in MODULES
        },
    }
    _hashed(workspace, "workspace_sha256")
    _schema("institutional workspace", workspace, INSTITUTIONAL_WORKSPACE_SCHEMA_PATH)
    return workspace
