"""Core scoring logic for Catalyst Narrative Risk.

The module uses transparent heuristics. It does not verify truth, certify evidence,
or replace human review. It helps make narrative-risk review more structured.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


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

SCALE_WEIGHTS = {
    "low": 3,
    "medium": 10,
    "high": 18,
}

CONSEQUENCE_WEIGHTS = {
    "low": 3,
    "moderate": 10,
    "high": 18,
    "critical": 24,
}

REVIEW_STATUS_WEIGHTS = {
    "reviewed": 0,
    "partly_reviewed": 8,
    "not_reviewed": 18,
}


@dataclass
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


def _clean_choice(value: str, allowed: Dict[str, int], default: str) -> str:
    value = (value or "").strip().lower()
    return value if value in allowed else default


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
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


def _review_actions(inp: NarrativeRiskInput, score: int) -> List[str]:
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


def score_narrative_risk(
    claim: str,
    source_type: str = "reputable_secondary",
    evidence_strength: str = "moderate",
    uncertainty: str = "medium",
    narrative_volatility: str = "medium",
    stakeholder_pressure: str = "medium",
    time_sensitivity: str = "medium",
    consequences: str = "moderate",
    review_status: str = "partly_reviewed",
    source_count: int = 2,
    method_notes: str = "",
) -> Dict[str, Any]:
    """Score a narrative-risk record using transparent heuristics."""
    inp = NarrativeRiskInput(
        claim=(claim or "").strip(),
        source_type=_clean_choice(source_type, SOURCE_WEIGHTS, "reputable_secondary"),
        evidence_strength=_clean_choice(evidence_strength, EVIDENCE_WEIGHTS, "moderate"),
        uncertainty=_clean_choice(uncertainty, SCALE_WEIGHTS, "medium"),
        narrative_volatility=_clean_choice(narrative_volatility, SCALE_WEIGHTS, "medium"),
        stakeholder_pressure=_clean_choice(stakeholder_pressure, SCALE_WEIGHTS, "medium"),
        time_sensitivity=_clean_choice(time_sensitivity, SCALE_WEIGHTS, "medium"),
        consequences=_clean_choice(consequences, CONSEQUENCE_WEIGHTS, "moderate"),
        review_status=_clean_choice(review_status, REVIEW_STATUS_WEIGHTS, "partly_reviewed"),
        source_count=max(0, int(source_count or 0)),
        method_notes=(method_notes or "").strip(),
    )

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

    raw = sum(components.values())
    # Scale a broad additive range into a stable 0-100 score.
    score = _clamp(raw * 0.68)
    level = _level(score)
    flags = _flags(inp, score)
    actions = _review_actions(inp, score)

    if level == "High":
        decision_note = "Do not use as a confident public claim without additional review, source support, and narrowed language."
    elif level == "Medium":
        decision_note = "Use cautiously with visible uncertainty, source links, and review notes."
    else:
        decision_note = "Risk appears lower by heuristic review, but source links and review date should still be preserved."

    return {
        "claim": inp.claim,
        "risk_score": score,
        "risk_level": level,
        "components": components,
        "flags": flags,
        "review_actions": actions,
        "decision_note": decision_note,
        "inputs": asdict(inp),
    }


def build_narrative_risk_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = score_narrative_risk(**payload)
    result["record_type"] = "catalyst_narrative_risk_record"
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["method"] = "transparent heuristic scoring; not truth verification"
    return result


# Backward-compatible shim for the older repository's test/demo shape.
def score_simple_risk(holdings, cash, total):  # pragma: no cover - compatibility only
    if total <= 0:
        return {"score": 0, "level": "Low", "concentration": 0.0,
                "symbols_count": 0, "cash_buffer": 1.0, "notes": "No assets"}
    largest = holdings[0]["value"] if holdings else 0.0
    concentration = largest / total
    symbols_count = len(holdings)
    cash_buffer = cash / total
    pts = 0
    if concentration >= 0.60: pts += 35
    elif concentration >= 0.40: pts += 25
    elif concentration >= 0.25: pts += 15
    elif concentration >= 0.15: pts += 8
    if symbols_count <= 1: pts += 20
    elif symbols_count == 2: pts += 12
    elif symbols_count <= 4: pts += 6
    if cash_buffer < 0.05: pts += 20
    elif cash_buffer < 0.10: pts += 12
    elif cash_buffer < 0.20: pts += 6
    pts = _clamp(pts)
    level = "High" if pts >= 60 else ("Medium" if pts >= 30 else "Low")
    notes = []
    if concentration >= 0.40: notes.append("High position concentration")
    if symbols_count <= 2: notes.append("Low diversification")
    if cash_buffer < 0.10: notes.append("Low cash buffer")
    if not notes: notes.append("Balanced by heuristics")
    return {"score": pts, "level": level, "concentration": concentration,
            "symbols_count": symbols_count, "cash_buffer": cash_buffer,
            "notes": "; ".join(notes)}
