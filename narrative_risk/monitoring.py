"""Narrative change, source freshness, snapshots, and monitoring primitives for v1.9.0.

Monitoring remains advisory. It detects changes and schedules reassessment but does
not alter analytical scores, approve content, or replace human review.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Mapping, Sequence
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from .contracts import (
    MONITORING_ALERT_SCHEMA_PATH,
    MONITORING_COMPARISON_SCHEMA_PATH,
    MONITORING_SNAPSHOT_SCHEMA_PATH,
    SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH,
    WATCHLIST_SCHEMA_PATH,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError

VERSION = "1.9.0"
SNAPSHOT_TRIGGERS = {"manual", "revision_created", "scheduled", "site_intelligence", "import"}
WATCH_STATUSES = {"active", "paused", "closed"}
WATCH_CADENCES = {"manual", "hourly", "daily", "weekly", "monthly"}
WATCH_TRIGGERS = {
    "new_evidence", "material_change", "source_stale", "source_content_changed",
    "risk_level_changed", "wording_changed", "confidence_changed",
    "reassessment_due", "approval_expired", "site_intelligence_event",
}
ALERT_TYPES = set(WATCH_TRIGGERS)
ALERT_SEVERITIES = {"info", "low", "medium", "high", "critical"}
ALERT_STATUSES = {"open", "acknowledged", "resolved"}
SITE_INTELLIGENCE_EVENT_TYPES = {"new_evidence", "material_change", "source_update", "narrative_shift"}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: str | None, field: str, *, required: bool = False) -> datetime | None:
    if value in (None, ""):
        if required:
            raise NarrativeRiskValidationError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string") from exc
    if parsed.tzinfo is None:
        raise NarrativeRiskValidationError(f"{field} must include a timezone")
    return parsed


def validate_datetime(value: str, field: str) -> str:
    parse_datetime(value, field, required=True)
    return value


def urn_uuid(value: str | None, field: str) -> str:
    if value is None:
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except (ValueError, AttributeError) as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def deterministic_urn(kind: str, payload: Mapping[str, Any]) -> str:
    return f"urn:uuid:{uuid5(NAMESPACE_URL, f'catalyst-narrative-risk:{kind}:{sha256_digest(payload)}')}"


def choice(value: Any, field: str, allowed: Iterable[str], *, default: str | None = None) -> str:
    if value in (None, ""):
        if default is None:
            raise NarrativeRiskValidationError(f"{field} is required")
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    allowed_set = set(allowed)
    if cleaned not in allowed_set:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(sorted(allowed_set))}")
    return cleaned


def text(value: Any, field: str, *, required: bool = False, maximum: int = 50000) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    if len(cleaned) > maximum:
        raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return cleaned


def string_list(value: Any, field: str, *, allowed: set[str] | None = None, maximum: int = 1000) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NarrativeRiskValidationError(f"{field} must be an array of strings")
    output: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        cleaned = text(item, f"{field}[{index}]", required=True, maximum=1000)
        if allowed is not None and cleaned not in allowed:
            raise NarrativeRiskValidationError(f"{field}[{index}] must be one of: {', '.join(sorted(allowed))}")
        if cleaned.casefold() not in seen:
            output.append(cleaned)
            seen.add(cleaned.casefold())
    if len(output) > maximum:
        raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum} values")
    return output


def _schema_error(label: str, value: Mapping[str, Any], schema_path) -> None:
    try:
        validate_against_schema(value, schema_path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


def monitoring_policy(method_snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    policy = deepcopy(dict(method_snapshot.get("monitoring_policy", {})))
    if not policy:
        raise NarrativeRiskValidationError("method_snapshot is missing monitoring_policy")
    return policy


def _source_reference_date(source: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> datetime | None:
    candidates: list[datetime] = []
    for field in ("accessed_at",):
        parsed = parse_datetime(source.get(field), f"source.{field}")
        if parsed:
            candidates.append(parsed)
    provenance = source.get("provenance", {})
    parsed = parse_datetime(provenance.get("imported_at"), "source.provenance.imported_at")
    if parsed:
        candidates.append(parsed)
    for item in evidence_items:
        if item.get("source_id") == source.get("source_id"):
            parsed = parse_datetime(item.get("captured_at"), "evidence_item.captured_at")
            if parsed:
                candidates.append(parsed)
    if candidates:
        return max(candidates)
    year = source.get("published_year")
    if isinstance(year, int):
        return datetime(year, 12, 31, tzinfo=timezone.utc)
    return None


def evaluate_source_freshness(
    record: Mapping[str, Any], *, at: str | None = None, method_snapshot: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    method = method_snapshot or record.get("method_snapshot", {})
    policy = monitoring_policy(method)
    reference = parse_datetime(at, "at") if at else datetime.now(timezone.utc)
    assert reference is not None
    ledger = record.get("evidence_ledger", {})
    evidence_items = list(ledger.get("evidence_items", []))
    source_states: list[dict[str, Any]] = []
    counts = {"current": 0, "aging": 0, "stale": 0, "unknown": 0}
    for source in ledger.get("sources", []):
        source_type = source.get("source_type", "unknown")
        thresholds = policy.get("source_age_days", {}).get(source_type, policy["source_age_days"]["default"])
        reference_date = _source_reference_date(source, evidence_items)
        if reference_date is None:
            age_days = None
            status = source.get("freshness") if source.get("freshness") in counts else "unknown"
        else:
            age_days = max(0, int((reference - reference_date).total_seconds() // 86400))
            if age_days <= int(thresholds["current_max"]):
                status = "current"
            elif age_days <= int(thresholds["aging_max"]):
                status = "aging"
            else:
                status = "stale"
        counts[status] += 1
        source_states.append({
            "source_id": source["source_id"], "title": source["title"], "source_type": source_type,
            "reference_at": reference_date.isoformat() if reference_date else None,
            "age_days": age_days, "freshness": status,
            "content_sha256": source.get("provenance", {}).get("content_sha256"),
        })
    total = len(source_states)
    stale_ratio = (counts["stale"] / total) if total else 0.0
    status = "unknown" if total == 0 else ("stale" if counts["stale"] else "aging" if counts["aging"] else "current")
    report = {
        "evaluated_at": reference.isoformat(), "status": status, "source_count": total,
        "counts": counts, "stale_ratio": round(stale_ratio, 6), "sources": source_states,
        "reassessment_recommended": bool(counts["stale"] or (counts["aging"] and record.get("normalized_input", {}).get("time_sensitivity") == "high")),
    }
    return report


def build_monitoring_snapshot(
    record: Mapping[str, Any], *, case_id: str | None = None, revision_id: str | None = None,
    governance: Mapping[str, Any] | None = None, captured_at: str | None = None,
    trigger: str = "manual", snapshot_id: str | None = None,
) -> Dict[str, Any]:
    if not isinstance(record, Mapping):
        raise NarrativeRiskValidationError("record must be a JSON object")
    timestamp = validate_datetime(captured_at, "captured_at") if captured_at else iso_now()
    normalized_trigger = choice(trigger, "trigger", SNAPSHOT_TRIGGERS, default="manual")
    identifiers = record.get("identifiers", {})
    normalized_case_id = urn_uuid(case_id or identifiers.get("case_id"), "case_id")
    normalized_revision_id = urn_uuid(revision_id, "revision_id") if revision_id else None
    record_id = identifiers.get("record_id")
    if not isinstance(record_id, str):
        raise NarrativeRiskValidationError("record.identifiers.record_id is required")
    ledger = record.get("evidence_ledger", {})
    narrative_map = record.get("narrative_map", {})
    claims = [
        {"claim_id": item["claim_id"], "text": item["text"], "claim_type": item.get("claim_type", "factual"), "role": item.get("role", "supporting")}
        for item in ledger.get("claims", [])
    ]
    nodes = [
        {"node_id": item["node_id"], "text": item["text"], "node_type": item["node_type"], "confidence_language": item.get("confidence_language", "unknown")}
        for item in narrative_map.get("nodes", [])
    ]
    links = [item["link_id"] for item in narrative_map.get("links", [])]
    evidence_ids = [item["evidence_id"] for item in ledger.get("evidence_items", [])]
    source_ids = [item["source_id"] for item in ledger.get("sources", [])]
    freshness = evaluate_source_freshness(record, at=timestamp)
    governance = dict(governance or {})
    governance_state = {
        "workflow_status": governance.get("status"),
        "final_disposition": governance.get("final_disposition"),
        "approval_valid_until": governance.get("approval_valid_until"),
        "reassessment_at": governance.get("reassessment_at"),
        "publication_allowed": bool(governance.get("publication_allowed", False)),
    }
    snapshot = {
        "snapshot_id": urn_uuid(snapshot_id, "snapshot_id"), "snapshot_version": VERSION,
        "case_id": normalized_case_id, "revision_id": normalized_revision_id, "record_id": record_id,
        "captured_at": timestamp, "trigger": normalized_trigger, "record_sha256": sha256_digest(record),
        "risk_score": int(record.get("calculations", {}).get("risk_score", 0)),
        "risk_level": record.get("interpretation", {}).get("risk_level", "Low"),
        "confidence_state": {
            "evidence_strength": record.get("normalized_input", {}).get("evidence_strength", "unclear"),
            "uncertainty": record.get("normalized_input", {}).get("uncertainty", "high"),
            "review_status": record.get("normalized_input", {}).get("review_status", "not_reviewed"),
        },
        "claims": claims, "narrative_nodes": nodes, "narrative_link_ids": links,
        "source_ids": source_ids, "evidence_ids": evidence_ids,
        "freshness_report": freshness, "governance_state": governance_state,
    }
    snapshot["snapshot_sha256"] = sha256_digest(snapshot)
    _schema_error("monitoring snapshot", snapshot, MONITORING_SNAPSHOT_SCHEMA_PATH)
    return snapshot


def _similarity(left: str, right: str) -> float:
    return round(SequenceMatcher(None, left.casefold(), right.casefold()).ratio(), 6)


def compare_monitoring_snapshots(
    previous: Mapping[str, Any], current: Mapping[str, Any], *, compared_at: str | None = None,
    method_snapshot: Mapping[str, Any], comparison_id: str | None = None,
) -> Dict[str, Any]:
    _schema_error("monitoring snapshot", previous, MONITORING_SNAPSHOT_SCHEMA_PATH)
    _schema_error("monitoring snapshot", current, MONITORING_SNAPSHOT_SCHEMA_PATH)
    if previous["case_id"] != current["case_id"]:
        raise NarrativeRiskValidationError("monitoring snapshots must belong to the same case")
    timestamp = validate_datetime(compared_at, "compared_at") if compared_at else iso_now()
    policy = monitoring_policy(method_snapshot)
    previous_claims = {item["claim_id"]: item for item in previous["claims"]}
    current_claims = {item["claim_id"]: item for item in current["claims"]}
    wording_changes = []
    for claim_id in sorted(set(previous_claims) | set(current_claims)):
        before = previous_claims.get(claim_id)
        after = current_claims.get(claim_id)
        if before is None:
            wording_changes.append({"claim_id": claim_id, "change_type": "added", "from_text": None, "to_text": after["text"], "similarity": 0.0})
        elif after is None:
            wording_changes.append({"claim_id": claim_id, "change_type": "removed", "from_text": before["text"], "to_text": None, "similarity": 0.0})
        elif before["text"] != after["text"]:
            wording_changes.append({"claim_id": claim_id, "change_type": "modified", "from_text": before["text"], "to_text": after["text"], "similarity": _similarity(before["text"], after["text"])})
    confidence_changes = []
    for field in ("evidence_strength", "uncertainty", "review_status"):
        before = previous["confidence_state"][field]
        after = current["confidence_state"][field]
        if before != after:
            confidence_changes.append({"field": field, "from": before, "to": after})
    previous_sources, current_sources = set(previous["source_ids"]), set(current["source_ids"])
    previous_evidence, current_evidence = set(previous["evidence_ids"]), set(current["evidence_ids"])
    previous_source_states = {item["source_id"]: item for item in previous["freshness_report"]["sources"]}
    current_source_states = {item["source_id"]: item for item in current["freshness_report"]["sources"]}
    content_changes = []
    freshness_changes = []
    for source_id in sorted(previous_sources & current_sources):
        before, after = previous_source_states[source_id], current_source_states[source_id]
        if before.get("content_sha256") and after.get("content_sha256") and before["content_sha256"] != after["content_sha256"]:
            content_changes.append(source_id)
        if before["freshness"] != after["freshness"]:
            freshness_changes.append({"source_id": source_id, "from": before["freshness"], "to": after["freshness"]})
    previous_nodes = {item["node_id"]: item for item in previous["narrative_nodes"]}
    current_nodes = {item["node_id"]: item for item in current["narrative_nodes"]}
    modified_nodes = []
    for node_id in sorted(set(previous_nodes) & set(current_nodes)):
        if previous_nodes[node_id] != current_nodes[node_id]:
            modified_nodes.append(node_id)
    narrative_changes = {
        "added_node_ids": sorted(set(current_nodes) - set(previous_nodes)),
        "removed_node_ids": sorted(set(previous_nodes) - set(current_nodes)),
        "modified_node_ids": modified_nodes,
        "added_link_ids": sorted(set(current["narrative_link_ids"]) - set(previous["narrative_link_ids"])),
        "removed_link_ids": sorted(set(previous["narrative_link_ids"]) - set(current["narrative_link_ids"])),
    }
    governance_changes = []
    for field in previous["governance_state"]:
        if previous["governance_state"].get(field) != current["governance_state"].get(field):
            governance_changes.append({"field": field, "from": previous["governance_state"].get(field), "to": current["governance_state"].get(field)})
    score_delta = current["risk_score"] - previous["risk_score"]
    risk_level_changed = previous["risk_level"] != current["risk_level"]
    weights = policy["materiality_weights"]
    materiality = min(100, int(
        min(abs(score_delta), 30) * weights["score_delta"]
        + len(wording_changes) * weights["wording_change"]
        + len(confidence_changes) * weights["confidence_change"]
        + len(current_sources - previous_sources) * weights["new_source"]
        + len(current_evidence - previous_evidence) * weights["new_evidence"]
        + len(content_changes) * weights["source_content_change"]
        + len(freshness_changes) * weights["freshness_change"]
        + (weights["risk_level_change"] if risk_level_changed else 0)
        + len(governance_changes) * weights["governance_change"]
    ))
    thresholds = policy["materiality_thresholds"]
    severity = "critical" if materiality >= thresholds["critical"] else "high" if materiality >= thresholds["high"] else "medium" if materiality >= thresholds["medium"] else "low" if materiality >= thresholds["low"] else "info"
    reasons = []
    if score_delta: reasons.append(f"Risk score changed by {score_delta:+d}.")
    if risk_level_changed: reasons.append(f"Risk level changed from {previous['risk_level']} to {current['risk_level']}.")
    if wording_changes: reasons.append(f"{len(wording_changes)} claim wording change(s) detected.")
    if confidence_changes: reasons.append(f"{len(confidence_changes)} confidence-state change(s) detected.")
    if current_sources - previous_sources: reasons.append(f"{len(current_sources - previous_sources)} new source(s) detected.")
    if current_evidence - previous_evidence: reasons.append(f"{len(current_evidence - previous_evidence)} new evidence item(s) detected.")
    if content_changes: reasons.append(f"{len(content_changes)} source content digest(s) changed.")
    if freshness_changes: reasons.append(f"{len(freshness_changes)} source freshness state(s) changed.")
    if governance_changes: reasons.append(f"{len(governance_changes)} governance state change(s) detected.")
    comparison = {
        "comparison_id": urn_uuid(comparison_id, "comparison_id"), "comparison_version": VERSION,
        "case_id": previous["case_id"], "from_snapshot_id": previous["snapshot_id"], "to_snapshot_id": current["snapshot_id"],
        "compared_at": timestamp, "score_delta": score_delta, "risk_level_changed": risk_level_changed,
        "wording_changes": wording_changes, "confidence_changes": confidence_changes,
        "evidence_changes": {
            "added_source_ids": sorted(current_sources - previous_sources), "removed_source_ids": sorted(previous_sources - current_sources),
            "added_evidence_ids": sorted(current_evidence - previous_evidence), "removed_evidence_ids": sorted(previous_evidence - current_evidence),
            "content_changed_source_ids": content_changes,
        },
        "narrative_changes": narrative_changes, "freshness_changes": freshness_changes,
        "governance_changes": governance_changes, "materiality_score": materiality,
        "severity": severity, "material_change": materiality >= thresholds["material"], "reasons": reasons,
    }
    comparison["comparison_sha256"] = sha256_digest(comparison)
    _schema_error("monitoring comparison", comparison, MONITORING_COMPARISON_SCHEMA_PATH)
    return comparison


def normalize_watchlist(payload: Mapping[str, Any], *, case_id: str | None = None) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("watchlist must be a JSON object")
    unknown = sorted(set(payload) - {
        "watch_id", "case_id", "name", "status", "cadence", "trigger_types", "source_ids", "created_at",
        "updated_at", "last_checked_at", "next_check_at", "created_by", "notes",
    })
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported watchlist field(s): {', '.join(unknown)}")
    timestamp = validate_datetime(payload.get("created_at"), "created_at") if payload.get("created_at") else iso_now()
    updated = validate_datetime(payload.get("updated_at"), "updated_at") if payload.get("updated_at") else timestamp
    watch = {
        "watch_id": urn_uuid(payload.get("watch_id"), "watch_id"), "watch_version": VERSION,
        "case_id": urn_uuid(case_id or payload.get("case_id"), "case_id"),
        "name": text(payload.get("name"), "name", required=True, maximum=500),
        "status": choice(payload.get("status"), "status", WATCH_STATUSES, default="active"),
        "cadence": choice(payload.get("cadence"), "cadence", WATCH_CADENCES, default="daily"),
        "trigger_types": string_list(payload.get("trigger_types") or ["material_change", "new_evidence", "source_stale", "reassessment_due"], "trigger_types", allowed=WATCH_TRIGGERS),
        "source_ids": string_list(payload.get("source_ids"), "source_ids", maximum=10000),
        "created_at": timestamp, "updated_at": updated,
        "last_checked_at": validate_datetime(payload["last_checked_at"], "last_checked_at") if payload.get("last_checked_at") else None,
        "next_check_at": validate_datetime(payload["next_check_at"], "next_check_at") if payload.get("next_check_at") else None,
        "created_by": text(payload.get("created_by"), "created_by", maximum=500) or None,
        "notes": text(payload.get("notes"), "notes", maximum=20000),
    }
    _schema_error("watchlist", watch, WATCHLIST_SCHEMA_PATH)
    return watch


def build_alert(
    *, case_id: str, alert_type: str, severity: str, title: str, body: str,
    watch_id: str | None = None, snapshot_id: str | None = None, comparison_id: str | None = None,
    metadata: Mapping[str, Any] | None = None, alert_id: str | None = None, created_at: str | None = None,
) -> Dict[str, Any]:
    alert = {
        "alert_id": urn_uuid(alert_id, "alert_id"), "alert_version": VERSION,
        "case_id": urn_uuid(case_id, "case_id"),
        "watch_id": urn_uuid(watch_id, "watch_id") if watch_id else None,
        "snapshot_id": urn_uuid(snapshot_id, "snapshot_id") if snapshot_id else None,
        "comparison_id": urn_uuid(comparison_id, "comparison_id") if comparison_id else None,
        "alert_type": choice(alert_type, "alert_type", ALERT_TYPES),
        "severity": choice(severity, "severity", ALERT_SEVERITIES),
        "title": text(title, "title", required=True, maximum=500), "body": text(body, "body", required=True),
        "status": "open", "created_at": validate_datetime(created_at, "created_at") if created_at else iso_now(),
        "acknowledged_at": None, "acknowledged_by": None, "resolved_at": None,
        "metadata": dict(metadata or {}),
    }
    _schema_error("monitoring alert", alert, MONITORING_ALERT_SCHEMA_PATH)
    return alert


def validate_site_intelligence_handoff(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("Site Intelligence handoff must be a JSON object")
    candidate = deepcopy(dict(payload))
    _schema_error("Site Intelligence monitoring handoff", candidate, SITE_INTELLIGENCE_HANDOFF_SCHEMA_PATH)
    return candidate
