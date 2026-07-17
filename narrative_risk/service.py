"""Canonical scoring engine for Catalyst Narrative Risk.

The engine uses transparent heuristics. It does not verify truth, certify evidence,
or replace human review. Python and browser runtimes share the same normalized
inputs, component weights, thresholds, flags, actions, and decision notes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

VERSION = "1.0.1"
RECORD_TYPE = "catalyst_narrative_risk_record"
METHOD = "transparent heuristic scoring; not truth verification"
SCHEMA_VERSION = "1.0.1"

SOURCE_WEIGHTS = {
    "official_or_primary": 0,
    "peer_reviewed_or_audited": 3,
    "reputable_secondary": 8,
    "internal_unreviewed": 14,
    "single_report_or_media": 18,
    "social_or_anecdotal": 24,
    "unknown": 28,
}

EVIDENCE_WEIGHTS = {
    "strong": 0,
    "moderate": 10,
    "limited": 20,
    "weak": 30,
    "unclear": 24,
}

SCALE_WEIGHTS = {"low": 3, "medium": 10, "high": 18}
CONSEQUENCE_WEIGHTS = {"low": 3, "moderate": 10, "high": 18, "critical": 24}
REVIEW_STATUS_WEIGHTS = {"reviewed": 0, "partly_reviewed": 8, "not_reviewed": 18}

INPUT_FIELDS = {
    "claim",
    "source_type",
    "evidence_strength",
    "uncertainty",
    "narrative_volatility",
    "stakeholder_pressure",
    "time_sensitivity",
    "consequences",
    "review_status",
    "source_count",
    "method_notes",
}


class NarrativeRiskValidationError(ValueError):
    """Raised when a narrative-risk payload cannot be normalized safely."""


@dataclass(frozen=True)
class NarrativeRiskInput:
    claim: str
    source_type: str = "reputable_secondary"
    evidence_strength: str = "moderate"
    uncertainty: str = "medium"
    narrative_volatility: str = "medium"
    stakeholder_pressure: str = "medium"
    time_sensitivity: str = "medium"
    consequences: str = "moderate"
    review_status: str = "partly_reviewed"
    source_count: int = 2
    method_notes: str = ""


def _clean_choice(value: Any, allowed: Mapping[str, int], default: str) -> str:
    if not isinstance(value, str):
        return default
    cleaned = value.strip().lower()
    return cleaned if cleaned in allowed else default


def _clean_text(value: Any, field: str, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    return cleaned


def _clean_source_count(value: Any) -> int:
    if value is None or value == "":
        return 0
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
    return parsed


def normalize_narrative_risk_input(payload: Mapping[str, Any]) -> NarrativeRiskInput:
    """Normalize a mapping into the canonical v1.0.1 input contract."""
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("payload must be a JSON object")
    unknown = sorted(set(payload) - INPUT_FIELDS)
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported input field(s): {', '.join(unknown)}")

    return NarrativeRiskInput(
        claim=_clean_text(payload.get("claim"), "claim", required=True),
        source_type=_clean_choice(payload.get("source_type", "reputable_secondary"), SOURCE_WEIGHTS, "reputable_secondary"),
        evidence_strength=_clean_choice(payload.get("evidence_strength", "moderate"), EVIDENCE_WEIGHTS, "moderate"),
        uncertainty=_clean_choice(payload.get("uncertainty", "medium"), SCALE_WEIGHTS, "medium"),
        narrative_volatility=_clean_choice(payload.get("narrative_volatility", "medium"), SCALE_WEIGHTS, "medium"),
        stakeholder_pressure=_clean_choice(payload.get("stakeholder_pressure", "medium"), SCALE_WEIGHTS, "medium"),
        time_sensitivity=_clean_choice(payload.get("time_sensitivity", "medium"), SCALE_WEIGHTS, "medium"),
        consequences=_clean_choice(payload.get("consequences", "moderate"), CONSEQUENCE_WEIGHTS, "moderate"),
        review_status=_clean_choice(payload.get("review_status", "partly_reviewed"), REVIEW_STATUS_WEIGHTS, "partly_reviewed"),
        source_count=_clean_source_count(payload.get("source_count", 2)),
        method_notes=_clean_text(payload.get("method_notes", ""), "method_notes"),
    )


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def _source_count_penalty(source_count: int) -> int:
    if source_count <= 0:
        return 22
    if source_count == 1:
        return 16
    if source_count == 2:
        return 8
    if source_count <= 4:
        return 3
    return 0


def _level(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _flags(inp: NarrativeRiskInput, score: int) -> List[str]:
    flags: List[str] = []
    if inp.source_count <= 1:
        flags.append("Single-source or under-sourced claim")
    if inp.evidence_strength in {"weak", "limited", "unclear"}:
        flags.append("Evidence does not yet support confident use")
    if inp.uncertainty == "high":
        flags.append("High uncertainty should be stated explicitly")
    if inp.narrative_volatility == "high":
        flags.append("Narrative may be changing quickly")
    if inp.stakeholder_pressure == "high":
        flags.append("Stakeholder pressure may be influencing interpretation")
    if inp.time_sensitivity == "high":
        flags.append("Time-sensitive claim requires recent source check")
    if inp.consequences in {"high", "critical"}:
        flags.append("High-consequence claim needs stricter review")
    if inp.review_status == "not_reviewed":
        flags.append("Claim has not completed review")
    if not flags and score < 40:
        flags.append("No major heuristic risk flags")
    return flags


def _review_actions(inp: NarrativeRiskInput) -> List[str]:
    actions: List[str] = []
    if inp.source_count <= 2:
        actions.append("Add at least one independent source or primary reference.")
    if inp.evidence_strength in {"weak", "limited", "unclear"}:
        actions.append("Rewrite claim with narrower language until evidence improves.")
    if inp.uncertainty == "high":
        actions.append("Add an uncertainty note that separates knowns, assumptions, and unknowns.")
    if inp.narrative_volatility == "high" or inp.time_sensitivity == "high":
        actions.append("Re-check source freshness before publication or decision use.")
    if inp.stakeholder_pressure == "high":
        actions.append("Document whether pressure, incentives, or reputational concerns may be shaping the claim.")
    if inp.consequences in {"high", "critical"}:
        actions.append("Escalate to domain, legal, compliance, or editorial review as appropriate.")
    if inp.review_status != "reviewed":
        actions.append("Record a reviewer, date, and decision before treating the claim as approved.")
    if not actions:
        actions.append("Maintain source links, method notes, and review date for future audit.")
    return actions


def score_narrative_risk(**payload: Any) -> Dict[str, Any]:
    """Score a narrative-risk payload using the canonical v1.0.1 heuristics."""
    inp = normalize_narrative_risk_input(payload)
    components = {
        "source_type": SOURCE_WEIGHTS[inp.source_type],
        "evidence_strength": EVIDENCE_WEIGHTS[inp.evidence_strength],
        "uncertainty": SCALE_WEIGHTS[inp.uncertainty],
        "narrative_volatility": SCALE_WEIGHTS[inp.narrative_volatility],
        "stakeholder_pressure": SCALE_WEIGHTS[inp.stakeholder_pressure],
        "time_sensitivity": SCALE_WEIGHTS[inp.time_sensitivity],
        "consequences": CONSEQUENCE_WEIGHTS[inp.consequences],
        "review_status": REVIEW_STATUS_WEIGHTS[inp.review_status],
        "source_count": _source_count_penalty(inp.source_count),
    }
    score = _clamp(sum(components.values()) * 0.68)
    risk_level = _level(score)

    if risk_level == "High":
        decision_note = "Do not use as a confident public claim without additional review, source support, and narrowed language."
    elif risk_level == "Medium":
        decision_note = "Use cautiously with visible uncertainty, source links, and review notes."
    else:
        decision_note = "Risk appears lower by heuristic review, but source links and review date should still be preserved."

    return {
        "claim": inp.claim,
        "risk_score": score,
        "risk_level": risk_level,
        "components": components,
        "flags": _flags(inp, score),
        "review_actions": _review_actions(inp),
        "decision_note": decision_note,
        "inputs": asdict(inp),
    }


def build_narrative_risk_record(payload: Mapping[str, Any], *, generated_at: str | None = None) -> Dict[str, Any]:
    """Build a complete export record from a canonical payload."""
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("payload must be a JSON object")
    result = score_narrative_risk(**dict(payload))
    result.update(
        {
            "record_type": RECORD_TYPE,
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "method": METHOD,
            "method_version": VERSION,
            "schema_version": SCHEMA_VERSION,
        }
    )
    return result


def validate_narrative_risk_record(record: Mapping[str, Any]) -> None:
    """Validate a generated record against the packaged JSON Schema."""
    try:
        import json
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("jsonschema is required to validate narrative-risk records") from exc

    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "narrative_risk_record.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(dict(record))
