"""First-party source handoff adapters for Knowledge Library and Catalyst Data."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from .contracts import (
    CATALYST_DATA_HANDOFF_SCHEMA_PATH,
    KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError
from .ledger import stable_ledger_id


def _validate(payload: Mapping[str, Any], schema_path, label: str) -> None:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError(f"{label} handoff must be a JSON object")
    try:
        validate_against_schema(payload, schema_path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label} handoff: {exc.message}") from exc
        raise


def import_knowledge_library_source(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Map a Knowledge Library document handoff into a ledger source input."""
    _validate(payload, KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA_PATH, "Knowledge Library")
    document_id = payload["document_id"]
    material = {"integration": "knowledge_library", "document_id": document_id}
    return {
        "source_id": stable_ledger_id("source", material),
        "title": payload["title"],
        "source_type": payload.get("source_type", "reputable_secondary"),
        "creators": payload.get("authors", []),
        "publisher": payload.get("publisher", ""),
        "published_year": payload.get("published_year"),
        "url": payload.get("canonical_url"),
        "accessed_at": payload.get("accessed_at"),
        "identifiers": [{"scheme": "catalog", "value": f"knowledge-library:{document_id}"}],
        "independence_group": f"knowledge-library:{document_id}",
        "duplicate_of_source_id": None,
        "directness": "unknown",
        "freshness": "unknown",
        "provenance": {
            "acquisition_method": "knowledge_library",
            "imported_from": f"knowledge-library:{document_id}",
            "imported_at": payload.get("accessed_at"),
            "content_sha256": payload.get("content_sha256"),
        },
        "notes": payload.get("notes", ""),
    }


def import_catalyst_data_source(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Map a Catalyst Data dataset handoff into a ledger source input."""
    _validate(payload, CATALYST_DATA_HANDOFF_SCHEMA_PATH, "Catalyst Data")
    dataset_id = payload["dataset_id"]
    material = {"integration": "catalyst_data", "dataset_id": dataset_id}
    return {
        "source_id": stable_ledger_id("source", material),
        "title": payload["title"],
        "source_type": payload.get("source_type", "official_or_primary"),
        "creators": payload.get("creators", []),
        "publisher": payload.get("publisher", ""),
        "published_year": payload.get("published_year"),
        "url": payload.get("landing_page"),
        "accessed_at": payload.get("accessed_at"),
        "identifiers": [{"scheme": "catalog", "value": f"catalyst-data:{dataset_id}"}],
        "independence_group": f"catalyst-data:{dataset_id}",
        "duplicate_of_source_id": None,
        "directness": "direct",
        "freshness": "unknown",
        "provenance": {
            "acquisition_method": "catalyst_data",
            "imported_from": f"catalyst-data:{dataset_id}",
            "imported_at": payload.get("accessed_at"),
            "content_sha256": payload.get("content_sha256"),
        },
        "notes": payload.get("notes", ""),
    }
