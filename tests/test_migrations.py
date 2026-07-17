import json
from pathlib import Path

from narrative_risk.migrations import migrate_record, migrate_v1_0_1_record, migrate_v1_1_0_record, migrate_v1_2_0_record
from narrative_risk.service import verify_record_reproducibility

FIXTURES = Path(__file__).parent / "fixtures"
LEGACY_V101 = json.loads((FIXTURES / "legacy-v1.0.1-record.json").read_text())
LEGACY_V110 = json.loads((FIXTURES / "legacy-v1.1.0-record.json").read_text())
LEGACY_V120 = json.loads((FIXTURES / "legacy-v1.2.0-record.json").read_text())


def test_v1_0_1_migration_preserves_score_and_level():
    migrated = migrate_v1_0_1_record(LEGACY_V101, migrated_at="2026-07-17T14:00:00+00:00")
    assert migrated["calculations"]["risk_score"] == LEGACY_V101["risk_score"]
    assert migrated["interpretation"]["risk_level"] == LEGACY_V101["risk_level"]
    assert migrated["migration"]["from_schema_version"] == "1.0.1"
    assert migrated["human_decision"]["disposition"] == "undecided"
    assert migrated["evidence_ledger"]["coverage"]["overall"]["source_count"] == 0
    assert verify_record_reproducibility(migrated)["exact_match"] is True


def test_v1_0_1_migration_assigns_deterministic_ids():
    first = migrate_v1_0_1_record(LEGACY_V101, migrated_at="2026-07-17T14:00:00+00:00")
    second = migrate_v1_0_1_record(LEGACY_V101, migrated_at="2026-07-17T15:00:00+00:00")
    assert first["identifiers"] == second["identifiers"]
    assert first["migration"]["migrated_at"] != second["migration"]["migrated_at"]


def test_v1_1_0_migration_preserves_analysis_human_decision_and_identifiers():
    migrated = migrate_v1_1_0_record(LEGACY_V110, migrated_at="2026-07-17T15:00:00+00:00")
    assert migrated["calculations"]["risk_score"] == LEGACY_V110["calculations"]["risk_score"]
    assert migrated["interpretation"]["risk_level"] == LEGACY_V110["interpretation"]["risk_level"]
    assert migrated["human_decision"] == LEGACY_V110["human_decision"]
    assert migrated["identifiers"]["record_id"] == LEGACY_V110["identifiers"]["record_id"]
    assert migrated["identifiers"]["case_id"] == LEGACY_V110["identifiers"]["case_id"]
    assert migrated["migration"]["from_schema_version"] == "1.1.0"
    assert verify_record_reproducibility(migrated)["exact_match"] is True


def test_v1_2_0_migration_preserves_ledger_analysis_decision_and_identifiers():
    migrated = migrate_v1_2_0_record(LEGACY_V120, migrated_at="2026-07-17T16:00:00+00:00")
    assert migrated["calculations"]["risk_score"] == LEGACY_V120["calculations"]["risk_score"]
    assert migrated["interpretation"]["risk_level"] == LEGACY_V120["interpretation"]["risk_level"]
    assert migrated["human_decision"] == LEGACY_V120["human_decision"]
    assert migrated["identifiers"]["record_id"] == LEGACY_V120["identifiers"]["record_id"]
    assert migrated["identifiers"]["case_id"] == LEGACY_V120["identifiers"]["case_id"]
    assert migrated["evidence_ledger"]["relationships"] == LEGACY_V120["evidence_ledger"]["relationships"]
    assert migrated["migration"]["from_schema_version"] == "1.2.0"
    assert verify_record_reproducibility(migrated)["exact_match"] is True


def test_auto_migration_detects_all_supported_versions():
    assert migrate_record(LEGACY_V101)["migration"]["from_schema_version"] == "1.0.1"
    assert migrate_record(LEGACY_V110)["migration"]["from_schema_version"] == "1.1.0"
    assert migrate_record(LEGACY_V120)["migration"]["from_schema_version"] == "1.2.0"
