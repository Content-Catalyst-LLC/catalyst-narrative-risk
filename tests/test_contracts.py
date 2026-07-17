from narrative_risk.contracts import (
    contract_definition,
    controlled_vocabularies,
    current_method_snapshot,
    sha256_digest,
)


def test_contract_registry_points_to_v1_1_0_assets():
    contract = contract_definition()
    assert contract["contract_version"] == "1.1.0"
    assert contract["layers"] == ["normalized_input", "calculations", "interpretation", "human_decision"]
    assert contract["compatibility"]["migrates_from"] == ["1.0.1"]


def test_method_and_vocabularies_are_version_aligned():
    method = current_method_snapshot()
    vocabs = controlled_vocabularies()
    assert method["controlled_vocabulary_id"] == vocabs["vocabulary_id"]
    assert method["controlled_vocabulary_version"] == vocabs["vocabulary_version"] == "1.1.0"
    assert set(method["weights"]["source_type"]) == set(vocabs["vocabularies"]["source_type"]["values"])
    assert len(sha256_digest(method)) == 64
