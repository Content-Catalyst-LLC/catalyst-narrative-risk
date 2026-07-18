"""Comparative narratives, scenarios, and sensitivity analysis for v2.0.0.

The comparative layer evaluates explicit records and assumptions. It does not
select a preferred narrative, certify truth, or silently modify canonical scores.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Sequence
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from .contracts import (
    COMPARISON_SET_SCHEMA_PATH, COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH,
    SCENARIO_SCHEMA_PATH, SCENARIO_RESULT_SCHEMA_PATH,
    SENSITIVITY_ANALYSIS_SCHEMA_PATH, COMPARATIVE_PORTFOLIO_SCHEMA_PATH,
    DECISION_STUDIO_HANDOFF_SCHEMA_PATH, current_method_snapshot,
    sha256_digest, validate_against_schema,
)
from .errors import NarrativeRiskValidationError
from .service import score_narrative_risk

VERSION = "2.0.0"
COMPARISON_STATUSES = {"draft", "active", "complete", "archived"}
COMPARISON_MODES = {"revision", "record", "scenario", "mixed"}
SCENARIO_TYPES = {"best_case", "base_case", "worst_case", "counterfactual", "adversarial", "custom"}
SCENARIO_STATUSES = {"draft", "active", "evaluated", "retired"}
ADJUSTMENT_OPERATIONS = {"add", "remove", "replace", "increase", "decrease", "hold"}
SCENARIO_OVERRIDE_FIELDS = {
    "source_type", "evidence_strength", "uncertainty", "narrative_volatility",
    "stakeholder_pressure", "time_sensitivity", "consequences", "review_status", "source_count",
}
SENSITIVITY_DIMENSIONS = tuple(sorted(SCENARIO_OVERRIDE_FIELDS))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def urn(value: str | None, field: str, *, material: Mapping[str, Any] | None = None) -> str:
    if value is None:
        if material is not None:
            return f"urn:uuid:{uuid5(NAMESPACE_URL, sha256_digest(material))}"
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except Exception as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def _text(value: Any, field: str, *, required: bool = False, maximum: int = 20000) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    value = value.strip()
    if required and not value:
        raise NarrativeRiskValidationError(f"{field} is required")
    if len(value) > maximum:
        raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return value


def _choice(value: Any, field: str, allowed: Iterable[str], default: str) -> str:
    if value in (None, ""):
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    value = value.strip().lower()
    if value not in allowed:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(sorted(allowed))}")
    return value


def _strings(value: Any, field: str, *, maximum: int = 100, item_maximum: int = 3000) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NarrativeRiskValidationError(f"{field} must be an array of strings")
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        clean = _text(item, f"{field}[{index}]", required=True, maximum=item_maximum)
        if clean not in seen:
            out.append(clean)
            seen.add(clean)
    if len(out) > maximum:
        raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum} values")
    return out


def _validate(label: str, value: Mapping[str, Any], schema_path) -> None:
    try:
        validate_against_schema(value, schema_path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


def normalize_comparison_member(payload: Mapping[str, Any], *, case_id: str, added_at: str | None = None) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("comparison member must be a JSON object")
    record_id = urn(payload.get("record_id"), "record_id")
    revision_id = payload.get("revision_id")
    label = _text(payload.get("label"), "label", required=True, maximum=500)
    return {
        "member_id": urn(payload.get("member_id"), "member_id", material={"case_id": case_id, "record_id": record_id, "label": label}),
        "label": label,
        "revision_id": urn(revision_id, "revision_id") if revision_id else None,
        "record_id": record_id,
        "frame": _text(payload.get("frame"), "frame", maximum=5000),
        "assumptions": _strings(payload.get("assumptions"), "assumptions"),
        "tags": _strings(payload.get("tags"), "tags", item_maximum=100),
        "selected": bool(payload.get("selected", True)),
        "added_at": added_at or payload.get("added_at") or iso_now(),
    }


def normalize_comparison_set(payload: Mapping[str, Any], *, case_id: str, created_at: str | None = None) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("comparison set must be a JSON object")
    normalized_case = urn(case_id, "case_id")
    timestamp = created_at or payload.get("created_at") or iso_now()
    members = [normalize_comparison_member(item, case_id=normalized_case, added_at=timestamp) for item in payload.get("members", [])]
    if len(members) < 2:
        raise NarrativeRiskValidationError("comparison set requires at least two members")
    ids = [item["member_id"] for item in members]
    if len(ids) != len(set(ids)):
        raise NarrativeRiskValidationError("comparison member_id values must be unique")
    record_ids = [item["record_id"] for item in members]
    if len(record_ids) != len(set(record_ids)):
        raise NarrativeRiskValidationError("comparison members must reference distinct records")
    baseline = payload.get("baseline_member_id") or members[0]["member_id"]
    baseline = urn(baseline, "baseline_member_id")
    if baseline not in ids:
        raise NarrativeRiskValidationError("baseline_member_id must reference a comparison member")
    value = {
        "comparison_id": urn(payload.get("comparison_id"), "comparison_id", material={"case_id": normalized_case, "title": payload.get("title", ""), "records": record_ids}),
        "case_id": normalized_case,
        "title": _text(payload.get("title"), "title", required=True, maximum=500),
        "description": _text(payload.get("description"), "description"),
        "status": _choice(payload.get("status"), "status", COMPARISON_STATUSES, "draft"),
        "comparison_mode": _choice(payload.get("comparison_mode"), "comparison_mode", COMPARISON_MODES, "revision"),
        "baseline_member_id": baseline,
        "members": members,
        "created_at": timestamp,
        "updated_at": payload.get("updated_at") or timestamp,
        "created_by": _text(payload.get("created_by"), "created_by", maximum=500) or None,
    }
    _validate("comparison set", value, COMPARISON_SET_SCHEMA_PATH)
    return value


def _claim_key(text: str) -> str:
    return " ".join(text.lower().split())[:500]


def build_evidence_matrix(comparison: Mapping[str, Any], records_by_id: Mapping[str, Mapping[str, Any]], *, generated_at: str | None = None, matrix_id: str | None = None) -> Dict[str, Any]:
    _validate("comparison set", comparison, COMPARISON_SET_SCHEMA_PATH)
    rows: dict[str, dict[str, Any]] = {}
    coverage_by_member: dict[str, dict[str, int]] = {}
    for member in comparison["members"]:
        record = records_by_id.get(member["record_id"])
        if record is None:
            raise NarrativeRiskValidationError(f"record not available for comparison member: {member['record_id']}")
        ledger = record["evidence_ledger"]
        claim_by_id = {item["claim_id"]: item for item in ledger["claims"]}
        coverage = {item["claim_id"]: item for item in ledger["coverage"]["per_claim"]}
        coverage_by_member[member["member_id"]] = {
            "covered_claims": sum(1 for item in coverage.values() if item["coverage_status"] not in {"none", "unsupported"}),
            "contested_claims": sum(1 for item in coverage.values() if item.get("contested")),
            "source_count": int(ledger["coverage"]["overall"]["source_count"]),
        }
        for claim_id, claim in claim_by_id.items():
            key = _claim_key(claim["text"])
            row = rows.setdefault(key, {"claim_key": key, "text": claim["text"], "member_cells": []})
            cov = coverage.get(claim_id, {})
            raw_status = cov.get("coverage_status", "none")
            if cov.get("contested"):
                status = "contested"
            elif raw_status in {"substantial", "strong"}:
                status = "strong"
            elif raw_status in {"adequate"}:
                status = "adequate"
            elif raw_status in {"partial", "limited"}:
                status = "partial"
            else:
                status = "none"
            row["member_cells"].append({
                "member_id": member["member_id"], "claim_ids": [claim_id], "coverage_status": status,
                "relationship_counts": {k: int(cov.get("relationship_counts", {}).get(k, 0)) for k in ("support", "qualify", "contradict", "contextualize", "unresolved")},
                "source_count": int(cov.get("source_count", 0)),
                "independent_source_count": int(cov.get("independent_source_count", 0)),
                "contradiction_count": int(cov.get("relationship_counts", {}).get("contradict", 0)),
            })
    member_ids = [item["member_id"] for item in comparison["members"]]
    claims = []
    for row in rows.values():
        existing = {cell["member_id"] for cell in row["member_cells"]}
        for member_id in member_ids:
            if member_id not in existing:
                row["member_cells"].append({"member_id": member_id, "claim_ids": [], "coverage_status": "none", "relationship_counts": {k: 0 for k in ("support", "qualify", "contradict", "contextualize", "unresolved")}, "source_count": 0, "independent_source_count": 0, "contradiction_count": 0})
        row["member_cells"].sort(key=lambda item: member_ids.index(item["member_id"]))
        signatures = {(cell["coverage_status"], cell["source_count"], cell["contradiction_count"]) for cell in row["member_cells"]}
        row["divergent"] = len(signatures) > 1
        claims.append(row)
    claims.sort(key=lambda item: item["claim_key"])
    value = {
        "matrix_id": urn(matrix_id, "matrix_id", material={"comparison_id": comparison["comparison_id"], "records": sorted(records_by_id)}),
        "comparison_id": comparison["comparison_id"], "case_id": comparison["case_id"],
        "generated_at": generated_at or iso_now(), "claims": claims,
        "summary": {"claim_count": len(claims), "member_count": len(member_ids), "divergence_count": sum(1 for item in claims if item["divergent"]), "coverage_by_member": coverage_by_member},
    }
    value["matrix_sha256"] = sha256_digest(value)
    _validate("comparative evidence matrix", value, COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH)
    return value


def _normalize_adjustments(value: Any, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NarrativeRiskValidationError(f"{field} must be an array")
    output = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NarrativeRiskValidationError(f"{field}[{index}] must be a JSON object")
        operation = _choice(item.get("operation"), f"{field}[{index}].operation", ADJUSTMENT_OPERATIONS, "hold")
        output.append({"target": _text(item.get("target"), f"{field}[{index}].target", required=True, maximum=500), "operation": operation, "value": deepcopy(item.get("value")), "rationale": _text(item.get("rationale"), f"{field}[{index}].rationale", maximum=5000)})
    return output


def normalize_scenario(payload: Mapping[str, Any], *, comparison_id: str, case_id: str, created_at: str | None = None) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("scenario must be a JSON object")
    timestamp = created_at or payload.get("created_at") or iso_now()
    overrides = deepcopy(payload.get("parameter_overrides") or {})
    if not isinstance(overrides, Mapping):
        raise NarrativeRiskValidationError("parameter_overrides must be a JSON object")
    unknown = sorted(set(overrides) - SCENARIO_OVERRIDE_FIELDS)
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported scenario override(s): {', '.join(unknown)}")
    probability = payload.get("probability")
    if probability is not None:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0 <= float(probability) <= 1:
            raise NarrativeRiskValidationError("probability must be null or a number from 0 to 1")
        probability = float(probability)
    value = {
        "scenario_id": urn(payload.get("scenario_id"), "scenario_id", material={"comparison_id": comparison_id, "name": payload.get("name", ""), "type": payload.get("scenario_type", "custom")}),
        "comparison_id": urn(comparison_id, "comparison_id"), "case_id": urn(case_id, "case_id"),
        "name": _text(payload.get("name"), "name", required=True, maximum=500),
        "scenario_type": _choice(payload.get("scenario_type"), "scenario_type", SCENARIO_TYPES, "custom"),
        "description": _text(payload.get("description"), "description"),
        "assumptions": _strings(payload.get("assumptions"), "assumptions"), "probability": probability,
        "parameter_overrides": dict(overrides),
        "evidence_adjustments": _normalize_adjustments(payload.get("evidence_adjustments"), "evidence_adjustments"),
        "narrative_adjustments": _normalize_adjustments(payload.get("narrative_adjustments"), "narrative_adjustments"),
        "status": _choice(payload.get("status"), "status", SCENARIO_STATUSES, "draft"),
        "created_at": timestamp, "updated_at": payload.get("updated_at") or timestamp,
        "created_by": _text(payload.get("created_by"), "created_by", maximum=500) or None,
    }
    _validate("scenario", value, SCENARIO_SCHEMA_PATH)
    return value


def _component_weights(analysis: Mapping[str, Any]) -> dict[str, int]:
    return {key: int(value["weight"]) for key, value in analysis["calculations"]["components"].items()}


def evaluate_scenario(scenario: Mapping[str, Any], comparison: Mapping[str, Any], records_by_id: Mapping[str, Mapping[str, Any]], *, generated_at: str | None = None, result_id: str | None = None) -> Dict[str, Any]:
    _validate("scenario", scenario, SCENARIO_SCHEMA_PATH)
    _validate("comparison set", comparison, COMPARISON_SET_SCHEMA_PATH)
    baseline_member = next((item for item in comparison["members"] if item["member_id"] == comparison["baseline_member_id"]), None)
    if baseline_member is None:
        raise NarrativeRiskValidationError("comparison baseline member is missing")
    record = records_by_id.get(baseline_member["record_id"])
    if record is None:
        raise NarrativeRiskValidationError("baseline record is not available")
    payload = deepcopy(record["normalized_input"])
    payload.update(scenario["parameter_overrides"])
    analysis = score_narrative_risk(payload, method_snapshot=record["method_snapshot"])
    baseline_score = int(record["calculations"]["risk_score"])
    current_score = int(analysis["calculations"]["risk_score"])
    baseline_components = {key: int(value["weight"]) for key, value in record["calculations"]["components"].items()}
    current_components = _component_weights(analysis)
    value = {
        "result_id": urn(result_id, "result_id", material={"scenario_id": scenario["scenario_id"], "baseline": baseline_member["record_id"], "overrides": scenario["parameter_overrides"]}),
        "scenario_id": scenario["scenario_id"], "comparison_id": scenario["comparison_id"], "case_id": scenario["case_id"],
        "baseline_member_id": baseline_member["member_id"], "generated_at": generated_at or iso_now(),
        "simulated_input": analysis["normalized_input"], "calculations": analysis["calculations"], "interpretation": analysis["interpretation"],
        "deltas": {"risk_score": current_score - baseline_score, "risk_level_changed": analysis["interpretation"]["risk_level"] != record["interpretation"]["risk_level"], "component_weights": {key: current_components.get(key, 0) - baseline_components.get(key, 0) for key in sorted(set(current_components) | set(baseline_components))}},
    }
    value["result_sha256"] = sha256_digest(value)
    _validate("scenario result", value, SCENARIO_RESULT_SCHEMA_PATH)
    return value


def _dimension_values(dimension: str, method: Mapping[str, Any]) -> list[Any]:
    if dimension == "source_count":
        return [0, 1, 2, 3, 5]
    if dimension in {"uncertainty", "narrative_volatility", "stakeholder_pressure", "time_sensitivity"}:
        return list(method["weights"]["three_level_scale"])
    return list(method["weights"][dimension])


def run_sensitivity_analysis(comparison: Mapping[str, Any], records_by_id: Mapping[str, Mapping[str, Any]], *, dimensions: Sequence[str] | None = None, generated_at: str | None = None, analysis_id: str | None = None) -> Dict[str, Any]:
    _validate("comparison set", comparison, COMPARISON_SET_SCHEMA_PATH)
    baseline_member = next(item for item in comparison["members"] if item["member_id"] == comparison["baseline_member_id"])
    record = records_by_id.get(baseline_member["record_id"])
    if record is None:
        raise NarrativeRiskValidationError("baseline record is not available")
    dims = list(dimensions or ("evidence_strength", "uncertainty", "stakeholder_pressure", "consequences", "source_count"))
    if not dims or len(set(dims)) != len(dims):
        raise NarrativeRiskValidationError("sensitivity dimensions must be a non-empty unique array")
    unknown = sorted(set(dims) - set(SENSITIVITY_DIMENSIONS))
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported sensitivity dimension(s): {', '.join(unknown)}")
    baseline_score = int(record["calculations"]["risk_score"])
    baseline = {"risk_score": baseline_score, "risk_level": record["interpretation"]["risk_level"], "component_weights": {key: int(value["weight"]) for key, value in record["calculations"]["components"].items()}}
    method = record.get("method_snapshot") or current_method_snapshot()
    runs = []
    for dimension in dims:
        for value in _dimension_values(dimension, method):
            payload = deepcopy(record["normalized_input"])
            payload[dimension] = value
            result = score_narrative_risk(payload, method_snapshot=method)
            runs.append({"run_id": urn(None, "run_id", material={"comparison_id": comparison["comparison_id"], "dimension": dimension, "value": value}), "dimension": dimension, "value": value, "risk_score": int(result["calculations"]["risk_score"]), "risk_level": result["interpretation"]["risk_level"], "delta_from_baseline": int(result["calculations"]["risk_score"]) - baseline_score, "component_weights": _component_weights(result)})
    drivers = []
    for dimension in dims:
        scores = [item["risk_score"] for item in runs if item["dimension"] == dimension]
        low, high = min(scores), max(scores)
        deltas = [item["delta_from_baseline"] for item in runs if item["dimension"] == dimension]
        if max(deltas) > 0 and min(deltas) < 0:
            direction = "mixed"
        elif max(deltas) > 0:
            direction = "increases_risk"
        elif min(deltas) < 0:
            direction = "decreases_risk"
        else:
            direction = "no_change"
        drivers.append({"dimension": dimension, "min_score": low, "max_score": high, "range": high - low, "direction": direction})
    drivers.sort(key=lambda item: (-item["range"], item["dimension"]))
    value = {"analysis_id": urn(analysis_id, "analysis_id", material={"comparison_id": comparison["comparison_id"], "dimensions": dims}), "comparison_id": comparison["comparison_id"], "case_id": comparison["case_id"], "baseline_member_id": baseline_member["member_id"], "dimensions": dims, "generated_at": generated_at or iso_now(), "baseline": baseline, "runs": runs, "drivers": drivers}
    value["analysis_sha256"] = sha256_digest(value)
    _validate("sensitivity analysis", value, SENSITIVITY_ANALYSIS_SCHEMA_PATH)
    return value


def build_comparative_portfolio(*, case_id: str, comparisons: Sequence[Mapping[str, Any]], records_by_id: Mapping[str, Mapping[str, Any]], scenarios: Sequence[Mapping[str, Any]], scenario_results: Sequence[Mapping[str, Any]], sensitivity_analyses: Sequence[Mapping[str, Any]], governance: Mapping[str, Any] | None = None, generated_at: str | None = None, portfolio_id: str | None = None) -> Dict[str, Any]:
    risk_distribution = {"Low": 0, "Medium": 0, "High": 0}
    member_ids: set[str] = set()
    for comparison in comparisons:
        for member in comparison["members"]:
            member_ids.add(member["member_id"])
            record = records_by_id.get(member["record_id"])
            if record:
                risk_distribution[record["interpretation"]["risk_level"]] += 1
    scores = [int(item["calculations"]["risk_score"]) for item in scenario_results]
    score_range = {"minimum": min(scores), "maximum": max(scores), "spread": max(scores)-min(scores)} if scores else None
    drivers=[]
    for analysis in sensitivity_analyses:
        for driver in analysis["drivers"]:
            if driver["range"] > 0 and driver["dimension"] not in drivers:
                drivers.append(driver["dimension"])
    workflow_status = (governance or {}).get("status")
    if governance is None:
        readiness = "not_assessed"
    elif not (governance or {}).get("publication_allowed", False):
        readiness = "blocked"
    elif (governance or {}).get("final_disposition") == "approve_with_conditions":
        readiness = "conditional"
    else:
        readiness = "ready"
    value = {"portfolio_id": urn(portfolio_id, "portfolio_id", material={"case_id": case_id, "comparison_ids": [item["comparison_id"] for item in comparisons]}), "case_id": urn(case_id, "case_id"), "generated_at": generated_at or iso_now(), "comparison_count": len(comparisons), "member_count": len(member_ids), "scenario_count": len(scenarios), "evaluated_scenario_count": len(scenario_results), "risk_distribution": risk_distribution, "scenario_score_range": score_range, "top_drivers": drivers[:10], "publication_readiness": readiness}
    value["portfolio_sha256"] = sha256_digest(value)
    _validate("comparative portfolio", value, COMPARATIVE_PORTFOLIO_SCHEMA_PATH)
    return value


def build_decision_studio_handoff(*, comparison: Mapping[str, Any], evidence_matrix: Mapping[str, Any] | None, scenario_results: Sequence[Mapping[str, Any]], sensitivity_analysis: Mapping[str, Any] | None, portfolio: Mapping[str, Any], governance: Mapping[str, Any] | None, selected_scenario_ids: Sequence[str] | None = None, generated_at: str | None = None, handoff_id: str | None = None) -> Dict[str, Any]:
    selected = [urn(value, "selected_scenario_id") for value in (selected_scenario_ids or [item["scenario_id"] for item in scenario_results])]
    available = {item["scenario_id"] for item in scenario_results}
    if not set(selected).issubset(available):
        raise NarrativeRiskValidationError("selected_scenario_ids must reference included scenario results")
    value = {"handoff_type": "catalyst_narrative_risk_decision_studio_handoff", "handoff_version": VERSION, "handoff_id": urn(handoff_id, "handoff_id", material={"comparison_id": comparison["comparison_id"], "selected": selected}), "case_id": comparison["case_id"], "comparison_id": comparison["comparison_id"], "selected_scenario_ids": selected, "comparison_set": deepcopy(dict(comparison)), "evidence_matrix": deepcopy(dict(evidence_matrix)) if evidence_matrix else None, "scenario_results": [deepcopy(dict(item)) for item in scenario_results if item["scenario_id"] in selected], "sensitivity_analysis": deepcopy(dict(sensitivity_analysis)) if sensitivity_analysis else None, "portfolio": deepcopy(dict(portfolio)), "governance": deepcopy(dict(governance or {})), "generated_at": generated_at or iso_now()}
    value["handoff_sha256"] = sha256_digest(value)
    _validate("Decision Studio handoff", value, DECISION_STUDIO_HANDOFF_SCHEMA_PATH)
    return value
