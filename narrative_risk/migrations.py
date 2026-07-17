"""Migration support for canonical Catalyst Narrative Risk records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping
from uuid import NAMESPACE_URL, uuid5

from .contracts import LEGACY_RECORD_SCHEMA_PATH, canonical_json, sha256_digest, validate_against_schema
from .service import NarrativeRiskValidationError, build_narrative_risk_record


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_urn(kind: str, legacy_record: Mapping[str, Any]) -> str:
    legacy_digest = sha256_digest(legacy_record)
    return f"urn:uuid:{uuid5(NAMESPACE_URL, f'catalyst-narrative-risk:{kind}:{legacy_digest}')}"


def migrate_v1_0_1_record(
    legacy_record: Mapping[str, Any],
    *,
    migrated_at: str | None = None,
) -> Dict[str, Any]:
    """Migrate a schema-valid v1.0.1 record into the v1.1.0 canonical contract."""
    if not isinstance(legacy_record, Mapping):
        raise NarrativeRiskValidationError("legacy_record must be a JSON object")
    try:
        validate_against_schema(legacy_record, LEGACY_RECORD_SCHEMA_PATH)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid v1.0.1 record: {exc.message}") from exc
        raise
    if legacy_record.get("schema_version") != "1.0.1" or legacy_record.get("method_version") != "1.0.1":
        raise NarrativeRiskValidationError("only v1.0.1 records can be migrated by this release")

    input_payload = dict(legacy_record["inputs"])
    review_status = input_payload.get("review_status")
    human_status = "reviewed" if review_status == "reviewed" else "pending_review"
    warnings = [
        "The v1.0.1 review_status field describes review completion; it does not establish an approval disposition.",
        "The migrated human disposition remains undecided until a reviewer records an explicit decision.",
    ]
    migration = {
        "from_schema_version": "1.0.1",
        "from_method_version": "1.0.1",
        "migrated_at": migrated_at or _iso_now(),
        "warnings": warnings,
    }
    migrated = build_narrative_risk_record(
        input_payload,
        generated_at=legacy_record["generated_at"],
        record_id=_deterministic_urn("record", legacy_record),
        case_id=_deterministic_urn("case", legacy_record),
        human_decision={
            "status": human_status,
            "disposition": "undecided",
            "reviewer_id": None,
            "reviewer_name": None,
            "reviewed_at": None,
            "notes": "Migrated from the v1.0.1 review record without inferring approval.",
        },
        migration=migration,
    )

    old_score = legacy_record["risk_score"]
    new_score = migrated["calculations"]["risk_score"]
    old_level = legacy_record["risk_level"]
    new_level = migrated["interpretation"]["risk_level"]
    if (old_score, old_level) != (new_score, new_level):
        raise NarrativeRiskValidationError(
            "migration changed the legacy analytical result: "
            f"{old_score}/{old_level} -> {new_score}/{new_level}"
        )
    return migrated
