"""Canonical v1.3.0 narrative-risk method and evidence-ledger engine.

The engine separates normalized scalar inputs, a traceable claims/sources/evidence
ledger, deterministic calculations, machine interpretation, and human decisions.
It structures review and does not verify truth or replace professional judgment.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Any, Dict, Iterable, List, Mapping
from uuid import UUID, uuid4

from .contracts import (
    INPUT_SCHEMA_PATH,
    METHOD_SCHEMA_PATH,
    RECORD_SCHEMA_PATH,
    canonical_json,
    contract_definition,
    current_method_snapshot,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError
from .ledger import build_evidence_ledger, ledger_input_from_record, ledger_interpretation

VERSION = "1.3.0"
METHOD_VERSION = "1.3.0"
SCHEMA_VERSION = "1.3.0"
RECORD_TYPE = "catalyst_narrative_risk_record"
CONTRACT_ID = "urn:catalyst:narrative-risk:contract:canonical"
METHOD_ID = "urn:catalyst:narrative-risk:method:transparent-heuristic"
SCHEMA_ID = "https://sustainablecatalyst.com/schemas/narrative-risk/record/1.3.0"
INPUT_SCHEMA_ID = "https://sustainablecatalyst.com/schemas/narrative-risk/input/1.3.0"
LEDGER_SCHEMA_ID = "https://sustainablecatalyst.com/schemas/narrative-risk/evidence-ledger/1.3.0"
METHOD = "transparent heuristic scoring with traceable evidence relationships; not truth verification"

SCALAR_INPUT_FIELDS = {
    "claim", "source_type", "evidence_strength", "uncertainty", "narrative_volatility",
    "stakeholder_pressure", "time_sensitivity", "consequences", "review_status", "source_count",
    "method_notes",
}
LEDGER_INPUT_FIELDS = {"claims", "sources", "evidence_items", "relationships"}
INPUT_FIELDS = SCALAR_INPUT_FIELDS | LEDGER_INPUT_FIELDS
HUMAN_DECISION_FIELDS = {"status", "disposition", "reviewer_id", "reviewer_name", "reviewed_at", "notes"}
HUMAN_DECISION_STATUS = {"draft", "pending_review", "reviewed"}
HUMAN_DISPOSITIONS = {"undecided", "approved", "approved_with_conditions", "revise", "rejected"}


@dataclass(frozen=True)
class NarrativeRiskInput:
    claim: str
    source_type: str
    evidence_strength: str
    uncertainty: str
    narrative_volatility: str
    stakeholder_pressure: str
    time_sensitivity: str
    consequences: str
    review_status: str
    source_count: int
    method_notes: str


def _clean_text(value: Any, field: str, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    return cleaned


def _clean_choice(value: Any, *, field: str, allowed: Iterable[str], default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    allowed_values = list(allowed)
    if cleaned not in allowed_values:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(allowed_values)}")
    return cleaned


def _clean_source_count(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise NarrativeRiskValidationError("source_count must be a non-negative integer")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and value.is_integer():
        parsed = int(value)
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or not cleaned.isdigit():
            raise NarrativeRiskValidationError("source_count must be a non-negative integer")
        parsed = int(cleaned)
    else:
        raise NarrativeRiskValidationError("source_count must be a non-negative integer")
    if parsed < 0:
        raise NarrativeRiskValidationError("source_count must be a non-negative integer")
    if parsed > 1_000_000:
        raise NarrativeRiskValidationError("source_count must be no greater than 1000000")
    return parsed


def validate_method_snapshot(method_snapshot: Mapping[str, Any]) -> None:
    if not isinstance(method_snapshot, Mapping):
        raise NarrativeRiskValidationError("method_snapshot must be a JSON object")
    try:
        validate_against_schema(method_snapshot, METHOD_SCHEMA_PATH)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid method_snapshot: {exc.message}") from exc
        raise


def _normalize_payload(
    payload: Mapping[str, Any],
    *,
    method_snapshot: Mapping[str, Any] | None = None,
) -> tuple[NarrativeRiskInput, Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("payload must be a JSON object")
    unknown = sorted(set(payload) - INPUT_FIELDS)
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported input field(s): {', '.join(unknown)}")

    method = deepcopy(dict(method_snapshot)) if method_snapshot is not None else current_method_snapshot()
    validate_method_snapshot(method)
    defaults = method["defaults"]
    weights = method["weights"]
    claim = _clean_text(payload.get("claim"), "claim", required=True)

    fallback = {
        "source_type": _clean_choice(payload.get("source_type"), field="source_type", allowed=weights["source_type"], default=defaults["source_type"]),
        "evidence_strength": _clean_choice(payload.get("evidence_strength"), field="evidence_strength", allowed=weights["evidence_strength"], default=defaults["evidence_strength"]),
        "source_count": _clean_source_count(payload.get("source_count"), int(defaults["source_count"])),
    }
    ledger = build_evidence_ledger(
        payload,
        narrative_claim=claim,
        method_snapshot=method,
        fallback_scoring_inputs=fallback,
    )
    derived = ledger["derived_scoring_inputs"]
    if derived["ledger_applied"]:
        for field in ("source_type", "evidence_strength", "source_count"):
            if field in payload and payload.get(field) not in (None, "") and fallback[field] != derived[field]:
                raise NarrativeRiskValidationError(
                    f"{field} conflicts with the value derived from the evidence ledger: {derived[field]}"
                )
        source_type = derived["source_type"]
        evidence_strength = derived["evidence_strength"]
        source_count = int(derived["source_count"])
    else:
        source_type = fallback["source_type"]
        evidence_strength = fallback["evidence_strength"]
        source_count = int(fallback["source_count"])

    normalized = NarrativeRiskInput(
        claim=claim,
        source_type=source_type,
        evidence_strength=evidence_strength,
        uncertainty=_clean_choice(payload.get("uncertainty"), field="uncertainty", allowed=weights["three_level_scale"], default=defaults["uncertainty"]),
        narrative_volatility=_clean_choice(payload.get("narrative_volatility"), field="narrative_volatility", allowed=weights["three_level_scale"], default=defaults["narrative_volatility"]),
        stakeholder_pressure=_clean_choice(payload.get("stakeholder_pressure"), field="stakeholder_pressure", allowed=weights["three_level_scale"], default=defaults["stakeholder_pressure"]),
        time_sensitivity=_clean_choice(payload.get("time_sensitivity"), field="time_sensitivity", allowed=weights["three_level_scale"], default=defaults["time_sensitivity"]),
        consequences=_clean_choice(payload.get("consequences"), field="consequences", allowed=weights["consequences"], default=defaults["consequences"]),
        review_status=_clean_choice(payload.get("review_status"), field="review_status", allowed=weights["review_status"], default=defaults["review_status"]),
        source_count=source_count,
        method_notes=_clean_text(payload.get("method_notes", defaults["method_notes"]), "method_notes"),
    )
    try:
        validate_against_schema(asdict(normalized), INPUT_SCHEMA_PATH)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid normalized input: {exc.message}") from exc
        raise
    return normalized, ledger


def normalize_narrative_risk_input(
    payload: Mapping[str, Any],
    *,
    method_snapshot: Mapping[str, Any] | None = None,
) -> NarrativeRiskInput:
    """Normalize scalar scoring inputs, including ledger-derived values."""
    normalized, _ledger = _normalize_payload(payload, method_snapshot=method_snapshot)
    return normalized


def _source_count_weight(source_count: int, ranges: List[Mapping[str, Any]]) -> int:
    for item in ranges:
        minimum = int(item["minimum"])
        maximum = item["maximum"]
        if source_count >= minimum and (maximum is None or source_count <= int(maximum)):
            return int(item["weight"])
    raise NarrativeRiskValidationError("method_snapshot has no source-count range for the normalized input")


def _half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def _threshold(score: int, method: Mapping[str, Any]) -> Dict[str, Any]:
    for threshold in method["algorithm"]["thresholds"]:
        if int(threshold["minimum"]) <= score <= int(threshold["maximum"]):
            return deepcopy(dict(threshold))
    raise NarrativeRiskValidationError("method_snapshot thresholds do not cover the calculated score")


def _evaluate_rule(rule: Mapping[str, Any], normalized: Mapping[str, Any], *, score: int, current: List[str]) -> bool:
    operator = rule["operator"]
    if operator == "if_empty":
        return not current
    if operator == "if_empty_and_score_lt":
        return not current and score < int(rule["value"])
    if operator == "any_eq":
        return any(normalized.get(field) == rule.get("value") for field in rule.get("fields", []))
    field = rule.get("field")
    actual = normalized.get(field)
    expected = rule.get("value")
    if operator == "lte":
        return actual <= expected
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "in":
        return actual in expected
    raise NarrativeRiskValidationError(f"unsupported method rule operator: {operator}")


def _apply_rules(rules: Iterable[Mapping[str, Any]], normalized: Mapping[str, Any], score: int) -> List[str]:
    output: List[str] = []
    for rule in rules:
        if _evaluate_rule(rule, normalized, score=score, current=output):
            output.append(str(rule["text"]))
    return output


def _append_unique(target: List[str], values: Iterable[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def score_narrative_risk(
    payload: Mapping[str, Any] | None = None,
    *,
    method_snapshot: Mapping[str, Any] | None = None,
    **fields: Any,
) -> Dict[str, Any]:
    """Return normalized input, evidence ledger, calculations, and interpretation."""
    if payload is not None and fields:
        raise NarrativeRiskValidationError("provide either payload or keyword fields, not both")
    source = payload if payload is not None else fields
    method = deepcopy(dict(method_snapshot)) if method_snapshot is not None else current_method_snapshot()
    validate_method_snapshot(method)
    inp, ledger = _normalize_payload(source, method_snapshot=method)
    normalized = asdict(inp)

    component_results: Dict[str, Dict[str, Any]] = {}
    for component_key in method["algorithm"]["component_order"]:
        metadata = method["components"][component_key]
        input_field = metadata["input_field"]
        input_value = normalized[input_field]
        table_name = metadata["weight_table"]
        if table_name == "source_count_penalties":
            weight = _source_count_weight(int(input_value), method["weights"][table_name])
        else:
            weight = int(method["weights"][table_name][input_value])
        component_results[component_key] = {
            "input_value": input_value,
            "weight": weight,
            "rationale": metadata["rationale"],
            "remediation": metadata["remediation"],
        }

    raw_total = sum(item["weight"] for item in component_results.values())
    multiplier = float(method["algorithm"]["multiplier"])
    scaled_score = round(raw_total * multiplier, 6)
    minimum = int(method["algorithm"]["minimum_score"])
    maximum = int(method["algorithm"]["maximum_score"])
    risk_score = max(minimum, min(maximum, _half_up(scaled_score)))
    threshold = _threshold(risk_score, method)
    risk_level = threshold["level"]

    interpretation_spec = method["interpretation"]
    flags = _apply_rules(interpretation_spec["flag_rules"], normalized, risk_score)
    actions = _apply_rules(interpretation_spec["action_rules"], normalized, risk_score)
    ledger_notes = ledger_interpretation(ledger, method)
    _append_unique(flags, ledger_notes["flags"])
    _append_unique(actions, ledger_notes["actions"])
    interpretation = {
        "risk_level": risk_level,
        "flags": flags,
        "review_actions": actions,
        "decision_note": interpretation_spec["decision_notes"][risk_level],
    }
    return {
        "normalized_input": normalized,
        "evidence_ledger": ledger,
        "calculations": {
            "components": component_results,
            "raw_total": raw_total,
            "multiplier": multiplier,
            "scaled_score": scaled_score,
            "risk_score": risk_score,
            "threshold": threshold,
        },
        "interpretation": interpretation,
    }


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


def _urn_uuid(value: str | None, field: str) -> str:
    if value is None:
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except (ValueError, AttributeError) as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def normalize_human_decision(payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    source = {} if payload is None else payload
    if not isinstance(source, Mapping):
        raise NarrativeRiskValidationError("human_decision must be a JSON object")
    unknown = sorted(set(source) - HUMAN_DECISION_FIELDS)
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported human_decision field(s): {', '.join(unknown)}")

    status = _clean_choice(source.get("status"), field="human_decision.status", allowed=HUMAN_DECISION_STATUS, default="draft")
    disposition = _clean_choice(source.get("disposition"), field="human_decision.disposition", allowed=HUMAN_DISPOSITIONS, default="undecided")
    reviewer_id = source.get("reviewer_id")
    reviewer_name = source.get("reviewer_name")
    reviewed_at = source.get("reviewed_at")
    for field, value in (("reviewer_id", reviewer_id), ("reviewer_name", reviewer_name)):
        if value is not None and not isinstance(value, str):
            raise NarrativeRiskValidationError(f"human_decision.{field} must be a string or null")
    if reviewed_at is not None:
        _validate_datetime(reviewed_at, "human_decision.reviewed_at")
    notes = _clean_text(source.get("notes", ""), "human_decision.notes")
    return {
        "status": status,
        "disposition": disposition,
        "reviewer_id": reviewer_id,
        "reviewer_name": reviewer_name,
        "reviewed_at": reviewed_at,
        "notes": notes,
    }


def build_narrative_risk_record(
    payload: Mapping[str, Any],
    *,
    generated_at: str | None = None,
    record_id: str | None = None,
    case_id: str | None = None,
    human_decision: Mapping[str, Any] | None = None,
    method_snapshot: Mapping[str, Any] | None = None,
    migration: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a complete v1.3.0 record with an embedded evidence ledger and method."""
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("payload must be a JSON object")
    method = deepcopy(dict(method_snapshot)) if method_snapshot is not None else current_method_snapshot()
    validate_method_snapshot(method)
    if method["method_id"] != METHOD_ID or method["method_version"] != METHOD_VERSION:
        raise NarrativeRiskValidationError("method_snapshot identifier or version is not supported by this release")

    analysis = score_narrative_risk(payload, method_snapshot=method)
    generated = _validate_datetime(generated_at, "generated_at") if generated_at is not None else _iso_now()
    contract = contract_definition()
    record: Dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "contract": {"contract_id": contract["contract_id"], "contract_version": contract["contract_version"]},
        "identifiers": {
            "record_id": _urn_uuid(record_id, "record_id"),
            "case_id": _urn_uuid(case_id, "case_id"),
            "method_id": method["method_id"],
            "schema_id": contract["record_schema_id"],
            "input_schema_id": contract["input_schema_id"],
            "ledger_schema_id": contract["ledger_schema_id"],
        },
        "generated_at": generated,
        "normalized_input": analysis["normalized_input"],
        "evidence_ledger": analysis["evidence_ledger"],
        "method_snapshot": method,
        "method_snapshot_sha256": sha256_digest(method),
        "calculations": analysis["calculations"],
        "interpretation": analysis["interpretation"],
        "human_decision": normalize_human_decision(human_decision),
    }
    if migration is not None:
        record["migration"] = deepcopy(dict(migration))
    record["reproducibility"] = {
        "canonical_input_sha256": sha256_digest(record["normalized_input"]),
        "evidence_ledger_sha256": sha256_digest(record["evidence_ledger"]),
        "record_payload_sha256": sha256_digest(record),
    }
    validate_narrative_risk_record(record)
    return record


def validate_narrative_risk_record(record: Mapping[str, Any]) -> None:
    if not isinstance(record, Mapping):
        raise NarrativeRiskValidationError("record must be a JSON object")
    try:
        validate_against_schema(record, RECORD_SCHEMA_PATH)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid narrative-risk record: {exc.message}") from exc
        raise


def reproduce_narrative_risk_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Rebuild a record from its normalized input, ledger, and method snapshot."""
    validate_narrative_risk_record(record)
    method = record["method_snapshot"]
    if sha256_digest(method) != record["method_snapshot_sha256"]:
        raise NarrativeRiskValidationError("method_snapshot_sha256 does not match the embedded method snapshot")
    payload = dict(record["normalized_input"])
    payload.update(ledger_input_from_record(record))
    return build_narrative_risk_record(
        payload,
        generated_at=record["generated_at"],
        record_id=record["identifiers"]["record_id"],
        case_id=record["identifiers"]["case_id"],
        human_decision=record["human_decision"],
        method_snapshot=method,
        migration=record.get("migration"),
    )


def verify_record_reproducibility(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Return deterministic verification for method, input, ledger, and record payload."""
    validate_narrative_risk_record(record)
    expected_method_hash = sha256_digest(record["method_snapshot"])
    payload = dict(record)
    reproducibility = payload.pop("reproducibility")
    expected_payload_hash = sha256_digest(payload)
    reproduced = reproduce_narrative_risk_record(record)
    exact_match = canonical_json(reproduced) == canonical_json(record)
    return {
        "exact_match": exact_match,
        "method_snapshot_hash_match": expected_method_hash == record["method_snapshot_sha256"],
        "canonical_input_hash_match": sha256_digest(record["normalized_input"]) == reproducibility["canonical_input_sha256"],
        "evidence_ledger_hash_match": sha256_digest(record["evidence_ledger"]) == reproducibility["evidence_ledger_sha256"],
        "record_payload_hash_match": expected_payload_hash == reproducibility["record_payload_sha256"],
        "record_id": record["identifiers"]["record_id"],
        "method_id": record["identifiers"]["method_id"],
        "method_version": record["method_snapshot"]["method_version"],
        "schema_id": record["identifiers"]["schema_id"],
        "ledger_schema_id": record["identifiers"]["ledger_schema_id"],
    }
