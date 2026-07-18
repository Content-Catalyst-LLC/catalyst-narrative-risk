from narrative_risk.contracts import (
    contract_definition,
    controlled_vocabularies,
    current_method_snapshot,
    sha256_digest,
)


def test_contract_registry_points_to_v1_10_0_assets():
    contract = contract_definition()
    assert contract["contract_version"] == "1.10.0"
    assert contract["layers"] == [
        "normalized_input", "evidence_ledger", "narrative_map", "calculations", "interpretation", "human_decision"
    ]
    assert contract["compatibility"]["migrates_from"] == ["1.0.1", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0", "1.7.0", "1.8.0", "1.9.0"]
    assert contract["ledger_schema_id"].endswith("/1.10.0")
    assert contract["narrative_map_schema_id"].endswith("/1.10.0")
    assert contract["knowledge_library_handoff_schema_id"].endswith("/1.10.0")
    assert contract["catalyst_data_handoff_schema_id"].endswith("/1.10.0")
    assert contract["briefing_schema_id"].endswith("/1.10.0")
    assert contract["publication_package_schema_id"].endswith("/1.10.0")
    assert contract["public_embed_schema_id"].endswith("/1.10.0")
    assert contract["api_key_schema_id"].endswith("/1.10.0")
    assert contract["platform_handoff_schema_id"].endswith("/1.10.0")


def test_method_and_vocabularies_are_version_aligned():
    method = current_method_snapshot()
    vocabs = controlled_vocabularies()
    assert method["controlled_vocabulary_id"] == vocabs["vocabulary_id"]
    assert method["controlled_vocabulary_version"] == vocabs["vocabulary_version"] == "1.10.0"
    assert method["ledger_policy"]["policy_version"] == "1.10.0"
    assert method["narrative_map_policy"]["policy_version"] == "1.10.0"
    assert method["publication_policy"]["policy_version"] == "1.10.0"
    assert set(method["weights"]["source_type"]) == set(vocabs["vocabularies"]["source_type"]["values"])
    assert set(method["ledger_policy"]["counted_relation_types"]) == set(
        vocabs["vocabularies"]["evidence_relation_type"]["values"]
    )
    assert len(sha256_digest(method)) == 64
