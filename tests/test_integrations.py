import json
from copy import deepcopy
from pathlib import Path

import pytest

from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.integrations import import_catalyst_data_source, import_knowledge_library_source

DATA = Path(__file__).resolve().parents[1] / "data" / "handoffs"
KNOWLEDGE = json.loads((DATA / "knowledge_library_source.json").read_text())
DATASET = json.loads((DATA / "catalyst_data_source.json").read_text())


def test_knowledge_library_handoff_maps_provenance_and_catalog_identifier():
    source = import_knowledge_library_source(KNOWLEDGE)
    assert source["source_id"].startswith("urn:catalyst:narrative-risk:source:sha256:")
    assert source["provenance"]["acquisition_method"] == "knowledge_library"
    assert source["provenance"]["imported_from"] == f"knowledge-library:{KNOWLEDGE['document_id']}"
    assert source["identifiers"] == [{"scheme": "catalog", "value": f"knowledge-library:{KNOWLEDGE['document_id']}"}]
    assert source["independence_group"] == f"knowledge-library:{KNOWLEDGE['document_id']}"


def test_catalyst_data_handoff_maps_dataset_as_direct_primary_source():
    source = import_catalyst_data_source(DATASET)
    assert source["source_type"] == "official_or_primary"
    assert source["directness"] == "direct"
    assert source["provenance"]["acquisition_method"] == "catalyst_data"
    assert source["identifiers"] == [{"scheme": "catalog", "value": f"catalyst-data:{DATASET['dataset_id']}"}]


def test_handoff_source_ids_are_deterministic_by_integration_identity():
    first = import_knowledge_library_source(KNOWLEDGE)
    changed_metadata = deepcopy(KNOWLEDGE)
    changed_metadata["title"] = "Updated title"
    second = import_knowledge_library_source(changed_metadata)
    assert first["source_id"] == second["source_id"]


@pytest.mark.parametrize(
    ("adapter", "payload", "label"),
    [
        (import_knowledge_library_source, {}, "invalid Knowledge Library handoff"),
        (import_catalyst_data_source, {}, "invalid Catalyst Data handoff"),
        (import_knowledge_library_source, "not-an-object", "Knowledge Library handoff must be a JSON object"),
    ],
)
def test_invalid_handoffs_are_rejected(adapter, payload, label):
    with pytest.raises(NarrativeRiskValidationError, match=label):
        adapter(payload)
