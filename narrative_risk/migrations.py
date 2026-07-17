"""Migration support for Catalyst Narrative Risk v1.4.0 records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping
from uuid import NAMESPACE_URL, uuid5

from .contracts import (
    LEGACY_V101_RECORD_SCHEMA_PATH,
    LEGACY_V110_RECORD_SCHEMA_PATH,
    LEGACY_V120_RECORD_SCHEMA_PATH,
    LEGACY_V130_RECORD_SCHEMA_PATH,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError
from .ledger import ledger_input_from_record
from .service import build_narrative_risk_record


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_urn(kind: str, legacy_record: Mapping[str, Any]) -> str:
    legacy_digest = sha256_digest(legacy_record)
    return f"urn:uuid:{uuid5(NAMESPACE_URL, f'catalyst-narrative-risk:{kind}:{legacy_digest}')}"


def _validate_legacy(record: Mapping[str, Any], path, label: str) -> None:
    if not isinstance(record, Mapping):
        raise NarrativeRiskValidationError("legacy_record must be a JSON object")
    try:
        validate_against_schema(record, path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label} record: {exc.message}") from exc
        raise


def _assert_preserved(legacy_score: int, legacy_level: str, migrated: Mapping[str, Any]) -> None:
    new_score = migrated["calculations"]["risk_score"]
    new_level = migrated["interpretation"]["risk_level"]
    if (legacy_score, legacy_level) != (new_score, new_level):
        raise NarrativeRiskValidationError(
            "migration changed the legacy analytical result: "
            f"{legacy_score}/{legacy_level} -> {new_score}/{new_level}"
        )


def migrate_v1_0_1_record(
    legacy_record: Mapping[str, Any],
    *,
    migrated_at: str | None = None,
) -> Dict[str, Any]:
    """Migrate a schema-valid v1.0.1 record into the v1.4.0 contract."""
    _validate_legacy(legacy_record, LEGACY_V101_RECORD_SCHEMA_PATH, "v1.0.1")
    if legacy_record.get("schema_version") != "1.0.1" or legacy_record.get("method_version") != "1.0.1":
        raise NarrativeRiskValidationError("only v1.0.1 records can be migrated by this function")

    input_payload = dict(legacy_record["inputs"])
    review_status = input_payload.get("review_status")
    human_status = "reviewed" if review_status == "reviewed" else "pending_review"
    migration = {
        "from_schema_version": "1.0.1",
        "from_method_version": "1.0.1",
        "migrated_at": migrated_at or _iso_now(),
        "warnings": [
            "The v1.0.1 review_status field does not establish an approval disposition.",
            "The legacy source count and evidence strength were retained because no item-level evidence ledger existed.",
            "A deterministic primary claim was created; sources and evidence must be added explicitly.",
        ],
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
            "notes": "Migrated from v1.0.1 without inferring approval or inventing evidence links.",
        },
        migration=migration,
    )
    _assert_preserved(legacy_record["risk_score"], legacy_record["risk_level"], migrated)
    return migrated


def migrate_v1_1_0_record(
    legacy_record: Mapping[str, Any],
    *,
    migrated_at: str | None = None,
) -> Dict[str, Any]:
    """Migrate a schema-valid v1.1.0 canonical record into v1.4.0."""
    _validate_legacy(legacy_record, LEGACY_V110_RECORD_SCHEMA_PATH, "v1.1.0")
    if legacy_record.get("contract", {}).get("contract_version") != "1.1.0":
        raise NarrativeRiskValidationError("only v1.1.0 records can be migrated by this function")

    migration = {
        "from_schema_version": "1.1.0",
        "from_method_version": "1.1.0",
        "migrated_at": migrated_at or _iso_now(),
        "warnings": [
            "The v1.1.0 scalar source assessment was retained because the record did not contain item-level sources or evidence relationships.",
            "A deterministic primary claim was created; the evidence ledger remains empty until sources and excerpts are added.",
            "Existing human review data was preserved without changing its disposition.",
        ],
    }
    migrated = build_narrative_risk_record(
        legacy_record["normalized_input"],
        generated_at=legacy_record["generated_at"],
        record_id=legacy_record["identifiers"]["record_id"],
        case_id=legacy_record["identifiers"]["case_id"],
        human_decision=legacy_record["human_decision"],
        migration=migration,
    )
    _assert_preserved(
        legacy_record["calculations"]["risk_score"],
        legacy_record["interpretation"]["risk_level"],
        migrated,
    )
    return migrated



def migrate_v1_2_0_record(
    legacy_record: Mapping[str, Any],
    *,
    migrated_at: str | None = None,
) -> Dict[str, Any]:
    """Migrate a schema-valid v1.2.0 evidence-ledger record into v1.4.0."""
    _validate_legacy(legacy_record, LEGACY_V120_RECORD_SCHEMA_PATH, "v1.2.0")
    if legacy_record.get("contract", {}).get("contract_version") != "1.2.0":
        raise NarrativeRiskValidationError("only v1.2.0 records can be migrated by this function")

    payload = dict(legacy_record["normalized_input"])
    payload.update(ledger_input_from_record(legacy_record))
    migration = {
        "from_schema_version": "1.2.0",
        "from_method_version": "1.2.0",
        "migrated_at": migrated_at or _iso_now(),
        "warnings": [
            "The v1.2.0 analytical record was preserved as a v1.3.0 immutable revision artifact.",
            "Case metadata, review events, saved views, and append-only activity are managed by the v1.3.0 workspace repository.",
            "Existing human review data and item-level evidence relationships were preserved without inferring new decisions.",
        ],
    }
    migrated = build_narrative_risk_record(
        payload,
        generated_at=legacy_record["generated_at"],
        record_id=legacy_record["identifiers"]["record_id"],
        case_id=legacy_record["identifiers"]["case_id"],
        human_decision=legacy_record["human_decision"],
        migration=migration,
    )
    _assert_preserved(
        legacy_record["calculations"]["risk_score"],
        legacy_record["interpretation"]["risk_level"],
        migrated,
    )
    return migrated



def migrate_v1_3_0_record(
    legacy_record: Mapping[str, Any],
    *,
    migrated_at: str | None = None,
) -> Dict[str, Any]:
    """Migrate a schema-valid v1.3.0 workspace-era record into v1.4.0."""
    _validate_legacy(legacy_record, LEGACY_V130_RECORD_SCHEMA_PATH, "v1.3.0")
    if legacy_record.get("contract", {}).get("contract_version") != "1.3.0":
        raise NarrativeRiskValidationError("only v1.3.0 records can be migrated by this function")

    payload = dict(legacy_record["normalized_input"])
    payload.update(ledger_input_from_record(legacy_record))
    migration = {
        "from_schema_version": "1.3.0",
        "from_method_version": "1.3.0",
        "migrated_at": migrated_at or _iso_now(),
        "warnings": [
            "The v1.3.0 analytical result, evidence ledger, and human decision were preserved.",
            "Narrative nodes were deterministically created from existing ledger claims because v1.3.0 did not store a narrative map.",
            "Reviewers should decompose compound claims and confirm causal, predictive, and assumption relationships explicitly.",
        ],
    }
    migrated = build_narrative_risk_record(
        payload, generated_at=legacy_record["generated_at"],
        record_id=legacy_record["identifiers"]["record_id"],
        case_id=legacy_record["identifiers"]["case_id"],
        human_decision=legacy_record["human_decision"], migration=migration,
    )
    _assert_preserved(legacy_record["calculations"]["risk_score"], legacy_record["interpretation"]["risk_level"], migrated)
    return migrated


def migrate_record(record: Mapping[str, Any], *, migrated_at: str | None = None) -> Dict[str, Any]:
    """Detect and migrate a supported legacy record."""
    if record.get("schema_version") == "1.0.1":
        return migrate_v1_0_1_record(record, migrated_at=migrated_at)
    if record.get("contract", {}).get("contract_version") == "1.1.0":
        return migrate_v1_1_0_record(record, migrated_at=migrated_at)
    if record.get("contract", {}).get("contract_version") == "1.2.0":
        return migrate_v1_2_0_record(record, migrated_at=migrated_at)
    if record.get("contract", {}).get("contract_version") == "1.3.0":
        return migrate_v1_3_0_record(record, migrated_at=migrated_at)
    raise NarrativeRiskValidationError("record is not a supported v1.0.1, v1.1.0, v1.2.0, or v1.3.0 legacy record")
