"""Review, approval, and governance policy primitives for v1.7.0.

This module deliberately keeps human governance separate from analytical scoring.
Scores, flags, and narrative diagnostics may inform reviewers, but only an
explicit, authorized governance decision can approve a revision for use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Sequence

from .contracts import current_method_snapshot
from .errors import NarrativeRiskValidationError

VERSION = "1.7.0"
REVIEW_STAGES = ("intake", "domain", "editorial", "legal", "compliance", "final")
WORKFLOW_STATUSES = {"draft", "active", "blocked", "changes_required", "approved", "rejected", "expired", "closed"}
ASSIGNMENT_STATUSES = {"pending", "accepted", "completed", "waived", "overdue"}
GOVERNANCE_DISPOSITIONS = {"approve", "approve_with_conditions", "revise", "reject", "waive"}
GOVERNANCE_ROLES = {
    "author", "reviewer", "domain_reviewer", "editorial_reviewer", "legal_reviewer",
    "compliance_reviewer", "final_approver", "administrator", "observer",
}
REVIEWER_ROLES = GOVERNANCE_ROLES - {"author", "observer"}
PUBLICATION_RESTRICTIONS = {
    "internal_only", "embargoed", "no_public_claim", "attribution_required",
    "legal_review_required", "disclosure_required",
}
PERMISSIONS = {
    "view", "comment", "submit_review", "assign_reviewers", "decide_stage",
    "approve_final", "manage_templates", "override_expiration", "publish",
}

DEFAULT_TEMPLATE_NAME = "Standard Narrative Risk Review"
DEFAULT_TEMPLATE_STAGES = [
    {"stage": "intake", "required": True, "required_role": "reviewer", "instructions": "Confirm scope, intended use, revision, and review pathway."},
    {"stage": "domain", "required": True, "required_role": "domain_reviewer", "instructions": "Review domain accuracy, evidence fit, assumptions, and uncertainty."},
    {"stage": "editorial", "required": True, "required_role": "editorial_reviewer", "instructions": "Review wording, framing, qualifications, citations, and audience suitability."},
    {"stage": "legal", "required": False, "required_role": "legal_reviewer", "instructions": "Review legal exposure, attribution, restrictions, and required notices."},
    {"stage": "compliance", "required": False, "required_role": "compliance_reviewer", "instructions": "Review policy, regulatory, disclosure, and records obligations."},
    {"stage": "final", "required": True, "required_role": "final_approver", "instructions": "Issue the final disposition and publication controls."},
]


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


def normalize_choice(value: Any, field: str, allowed: Iterable[str], *, default: str | None = None) -> str:
    if value in (None, ""):
        if default is None:
            raise NarrativeRiskValidationError(f"{field} is required")
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    values = sorted(set(allowed))
    if cleaned not in values:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(values)}")
    return cleaned


def normalize_string_list(value: Any, field: str, *, allowed: set[str] | None = None, maximum: int = 100, item_maximum: int = 5000) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NarrativeRiskValidationError(f"{field} must be an array of strings")
    result: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, str):
            raise NarrativeRiskValidationError(f"{field}[{index}] must be a string")
        item = raw.strip()
        if not item:
            raise NarrativeRiskValidationError(f"{field}[{index}] must not be empty")
        if len(item) > item_maximum:
            raise NarrativeRiskValidationError(f"{field}[{index}] must be no longer than {item_maximum} characters")
        if allowed is not None and item not in allowed:
            raise NarrativeRiskValidationError(f"{field}[{index}] must be one of: {', '.join(sorted(allowed))}")
        key = item.casefold()
        if key not in seen:
            result.append(item)
            seen.add(key)
    if len(result) > maximum:
        raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum} values")
    return result


def permissions_for_role(role: str, *, method_snapshot: Mapping[str, Any] | None = None) -> set[str]:
    normalized = normalize_choice(role, "actor_role", GOVERNANCE_ROLES)
    method = method_snapshot or current_method_snapshot()
    permissions = set(method.get("governance_policy", {}).get("permissions", {}).get(normalized, []))
    unknown = permissions - PERMISSIONS
    if unknown:
        raise NarrativeRiskValidationError(f"governance policy contains unsupported permission(s): {', '.join(sorted(unknown))}")
    return permissions


def require_permission(role: str, permission: str, *, method_snapshot: Mapping[str, Any] | None = None) -> None:
    if permission not in PERMISSIONS:
        raise NarrativeRiskValidationError(f"unsupported governance permission: {permission}")
    if permission not in permissions_for_role(role, method_snapshot=method_snapshot):
        raise NarrativeRiskValidationError(f"role {role} does not have permission: {permission}")


def default_template_payload() -> Dict[str, Any]:
    return {
        "name": DEFAULT_TEMPLATE_NAME,
        "description": "Default staged review for evidence, domain, editorial, optional legal/compliance, and final approval.",
        "stages": [dict(item) for item in DEFAULT_TEMPLATE_STAGES],
        "default_due_days": 14,
        "escalation_days": 3,
        "active": True,
    }


def normalize_template_stages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise NarrativeRiskValidationError("stages must be a non-empty array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous_index = -1
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise NarrativeRiskValidationError(f"stages[{index}] must be a JSON object")
        unknown = sorted(set(raw) - {"stage", "required", "required_role", "instructions"})
        if unknown:
            raise NarrativeRiskValidationError(f"unsupported stages[{index}] field(s): {', '.join(unknown)}")
        stage = normalize_choice(raw.get("stage"), f"stages[{index}].stage", REVIEW_STAGES)
        if stage in seen:
            raise NarrativeRiskValidationError(f"stages contains duplicate stage: {stage}")
        stage_index = REVIEW_STAGES.index(stage)
        if stage_index <= previous_index:
            raise NarrativeRiskValidationError("stages must follow canonical review-stage order")
        previous_index = stage_index
        seen.add(stage)
        required = raw.get("required", True)
        if not isinstance(required, bool):
            raise NarrativeRiskValidationError(f"stages[{index}].required must be a boolean")
        required_role = normalize_choice(raw.get("required_role"), f"stages[{index}].required_role", REVIEWER_ROLES)
        instructions = raw.get("instructions", "")
        if not isinstance(instructions, str):
            raise NarrativeRiskValidationError(f"stages[{index}].instructions must be a string")
        instructions = instructions.strip()
        if len(instructions) > 20000:
            raise NarrativeRiskValidationError(f"stages[{index}].instructions must be no longer than 20000 characters")
        result.append({"stage": stage, "required": required, "required_role": required_role, "instructions": instructions})
    if "final" not in seen:
        raise NarrativeRiskValidationError("review template must include a final stage")
    if next(item for item in result if item["stage"] == "final")["required"] is not True:
        raise NarrativeRiskValidationError("final review stage must be required")
    return result


def is_past(value: str | None, *, at: str | None = None) -> bool:
    target = parse_datetime(value, "date")
    if target is None:
        return False
    reference = parse_datetime(at, "at") if at else datetime.now(timezone.utc)
    assert reference is not None
    return target < reference
