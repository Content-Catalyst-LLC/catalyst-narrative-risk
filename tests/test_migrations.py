import json
from pathlib import Path

from narrative_risk.migrations import migrate_v1_0_1_record
from narrative_risk.service import verify_record_reproducibility

LEGACY = json.loads((Path(__file__).parent / "fixtures" / "legacy-v1.0.1-record.json").read_text())


def test_v1_0_1_migration_preserves_score_and_level():
    migrated = migrate_v1_0_1_record(LEGACY, migrated_at="2026-07-17T14:00:00+00:00")
    assert migrated["calculations"]["risk_score"] == LEGACY["risk_score"]
    assert migrated["interpretation"]["risk_level"] == LEGACY["risk_level"]
    assert migrated["migration"]["from_schema_version"] == "1.0.1"
    assert migrated["human_decision"]["disposition"] == "undecided"
    assert verify_record_reproducibility(migrated)["exact_match"] is True


def test_v1_0_1_migration_assigns_deterministic_ids():
    first = migrate_v1_0_1_record(LEGACY, migrated_at="2026-07-17T14:00:00+00:00")
    second = migrate_v1_0_1_record(LEGACY, migrated_at="2026-07-17T15:00:00+00:00")
    assert first["identifiers"] == second["identifiers"]
    assert first["migration"]["migrated_at"] != second["migration"]["migrated_at"]
