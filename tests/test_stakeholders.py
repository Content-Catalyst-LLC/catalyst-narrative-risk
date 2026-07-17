import json
from pathlib import Path
import pytest

from app import create_app
from narrative_risk.errors import NarrativeRiskValidationError
from narrative_risk.stakeholders import (
    build_stakeholder_intelligence, normalize_actor, normalize_incentive,
    normalize_pressure, normalize_relationship, normalize_consequence,
    validate_canvas_handoff,
)
from narrative_risk.workspaces import SQLiteCaseRepository

CASE_ID = "urn:uuid:77000000-0000-4000-8000-000000000001"
ACTOR_A = "urn:uuid:77000000-0000-4000-8000-000000000002"
ACTOR_B = "urn:uuid:77000000-0000-4000-8000-000000000003"


def actor(actor_id=ACTOR_A, name="Program funder", **changes):
    payload={"actor_id":actor_id,"name":name,"actor_type":"funder","influence":"high","stance":"supportive","disclosure_status":"disclosed","created_at":"2026-07-17T19:00:00+00:00"}
    payload.update(changes); return normalize_actor(payload,case_id=CASE_ID)


def test_actor_normalization_is_schema_valid_and_deterministic():
    value=actor(); assert value["actor_id"]==ACTOR_A; assert value["interests"]==[]; assert value["case_id"]==CASE_ID
    first=normalize_actor({"name":"Community","actor_type":"community"},case_id=CASE_ID,created_at="2026-07-17T19:00:00+00:00")
    second=normalize_actor({"name":"Community","actor_type":"community"},case_id=CASE_ID,created_at="2026-07-17T19:00:00+00:00")
    assert first["actor_id"]==second["actor_id"]


def test_relationship_rejects_self_link():
    with pytest.raises(NarrativeRiskValidationError,match="different actors"):
        normalize_relationship({"source_actor_id":ACTOR_A,"target_actor_id":ACTOR_A},case_id=CASE_ID)


def test_confirmed_conflict_requires_evidence():
    with pytest.raises(NarrativeRiskValidationError,match="requires at least one evidence_id"):
        normalize_incentive({"actor_id":ACTOR_A,"description":"Continued funding depends on positive results.","conflict_status":"confirmed"},case_id=CASE_ID)


def test_intelligence_derives_pressure_and_flags_without_changing_score():
    actors=[actor(),actor(ACTOR_B,"Independent evaluator",actor_type="research_institution",stance="neutral")]
    incentives=[normalize_incentive({"actor_id":ACTOR_A,"incentive_type":"financial","description":"Renewal funding depends on reported impact.","magnitude":"high","conflict_status":"potential","disclosed":False},case_id=CASE_ID,created_at="2026-07-17T19:01:00+00:00")]
    pressures=[normalize_pressure({"actor_id":ACTOR_B,"source_actor_id":ACTOR_A,"pressure_type":"funding","description":"Accelerate publication before renewal review.","intensity":"high"},case_id=CASE_ID,created_at="2026-07-17T19:02:00+00:00")]
    consequences=[normalize_consequence({"actor_id":ACTOR_B,"impact_type":"reputational","direction":"harm","severity":"high","description":"Overstatement could harm evaluator credibility."},case_id=CASE_ID,created_at="2026-07-17T19:03:00+00:00")]
    result=build_stakeholder_intelligence(case_id=CASE_ID,actors=actors,relationships=[],incentives=incentives,pressures=pressures,consequences=consequences,generated_at="2026-07-17T19:04:00+00:00")
    assert result["suggested_stakeholder_pressure"]=="high"
    assert any(flag.startswith("potential_conflict") for flag in result["flags"])
    assert any(flag.startswith("undisclosed_incentive") for flag in result["flags"])
    assert result["intelligence_sha256"]


def test_repository_persists_complete_stakeholder_graph(tmp_path):
    repo=SQLiteCaseRepository(tmp_path/"stakeholders.sqlite3")
    case=repo.create_case(case_id=CASE_ID,title="Stakeholder case")
    a=repo.add_stakeholder_actor(case["case_id"],{"actor_id":ACTOR_A,"name":"Funder","actor_type":"funder","influence":"high"})
    b=repo.add_stakeholder_actor(case["case_id"],{"actor_id":ACTOR_B,"name":"Evaluator","actor_type":"research_institution","influence":"high"})
    repo.add_stakeholder_relationship(case["case_id"],{"source_actor_id":a["actor_id"],"target_actor_id":b["actor_id"],"relationship_type":"funds","strength":"high"})
    repo.add_stakeholder_incentive(case["case_id"],{"actor_id":a["actor_id"],"incentive_type":"reputational","description":"Demonstrate impact.","magnitude":"high","conflict_status":"potential"})
    repo.add_stakeholder_pressure(case["case_id"],{"actor_id":b["actor_id"],"source_actor_id":a["actor_id"],"pressure_type":"deadline","description":"Publish before board review.","intensity":"critical"})
    repo.add_stakeholder_consequence(case["case_id"],{"actor_id":b["actor_id"],"impact_type":"reputational","direction":"harm","severity":"high","description":"Credibility damage."})
    summary=repo.get_stakeholder_intelligence(case["case_id"],generated_at="2026-07-17T20:00:00+00:00")
    assert summary["counts"]=={"actors":2,"relationships":1,"incentives":1,"pressures":1,"consequences":1}
    assert repo.get_case(case["case_id"])["stakeholder_actor_count"]==2
    repo.close()


def test_relationship_rejects_actor_from_another_case(tmp_path):
    repo=SQLiteCaseRepository(tmp_path/"cases.sqlite3")
    left=repo.create_case(title="Left"); right=repo.create_case(title="Right")
    a=repo.add_stakeholder_actor(left["case_id"],{"name":"A"}); b=repo.add_stakeholder_actor(right["case_id"],{"name":"B"})
    with pytest.raises(NarrativeRiskValidationError,match="another case"):
        repo.add_stakeholder_relationship(left["case_id"],{"source_actor_id":a["actor_id"],"target_actor_id":b["actor_id"]})
    repo.close()


def test_canvas_handoff_import_preserves_external_ids_and_relationships(tmp_path):
    payload=json.loads((Path(__file__).resolve().parents[1]/"data/handoffs/catalyst_canvas_stakeholder_handoff.json").read_text())
    validate_canvas_handoff(payload)
    repo=SQLiteCaseRepository(tmp_path/"canvas.sqlite3"); case=repo.create_case(title="Canvas import")
    result=repo.import_catalyst_canvas_stakeholders(case["case_id"],payload,imported_at="2026-07-17T20:00:00+00:00")
    assert len(result["actors"])==3; assert len(result["relationships"])==2
    assert all(item["external_id"].startswith("catalyst-canvas:canvas:energy-pilot:") for item in result["actors"])
    assert repo.list_canvas_handoffs(case["case_id"])[0]["handoff_sha256"]
    repo.close()


def test_bundle_round_trip_includes_stakeholder_intelligence(tmp_path):
    source=SQLiteCaseRepository(tmp_path/"source.sqlite3"); case=source.create_case(title="Bundle")
    actor_value=source.add_stakeholder_actor(case["case_id"],{"name":"Public regulator","actor_type":"regulator","influence":"critical"})
    source.add_stakeholder_pressure(case["case_id"],{"actor_id":actor_value["actor_id"],"pressure_type":"legal","description":"Statutory reporting deadline.","intensity":"high"})
    bundle=source.export_case_bundle(case["case_id"],exported_at="2026-07-17T21:00:00+00:00")
    report=source.verify_bundle(bundle); assert report["stakeholder_case_ids_match"]; assert report["stakeholder_intelligence_hash_match"]
    target=SQLiteCaseRepository(tmp_path/"target.sqlite3"); target.import_case_bundle(bundle)
    assert target.export_case_bundle(case["case_id"],exported_at="2026-07-17T21:00:00+00:00")==bundle
    source.close(); target.close()


def test_api_stakeholder_workflow(tmp_path):
    client=create_app({"NARRATIVE_RISK_DATABASE":str(tmp_path/"api.sqlite3")}).test_client()
    case=client.post("/api/narrative-risk/cases",json={"title":"API stakeholders"}).get_json()
    actor_response=client.post(f"/api/narrative-risk/cases/{case['case_id']}/stakeholders/actors",json={"name":"Media partner","actor_type":"media","influence":"high"})
    assert actor_response.status_code==201; actor_id=actor_response.get_json()["actor_id"]
    pressure=client.post(f"/api/narrative-risk/cases/{case['case_id']}/stakeholders/pressures",json={"actor_id":actor_id,"pressure_type":"media","description":"Breaking-news deadline.","intensity":"high"})
    assert pressure.status_code==201
    summary=client.get(f"/api/narrative-risk/cases/{case['case_id']}/stakeholder-intelligence?generated_at=2026-07-17T21:00:00%2B00:00")
    assert summary.status_code==200; assert summary.get_json()["suggested_stakeholder_pressure"]=="high"


def test_api_canvas_handoff(tmp_path):
    client=create_app({"NARRATIVE_RISK_DATABASE":str(tmp_path/"api-canvas.sqlite3")}).test_client(); case=client.post("/api/narrative-risk/cases",json={"title":"Canvas"}).get_json()
    payload=json.loads((Path(__file__).resolve().parents[1]/"data/handoffs/catalyst_canvas_stakeholder_handoff.json").read_text())
    response=client.post(f"/api/narrative-risk/cases/{case['case_id']}/import/catalyst-canvas",json=payload)
    assert response.status_code==201; assert response.get_json()["intelligence"]["counts"]["actors"]==3


def test_canvas_handoff_rejects_missing_target():
    payload=json.loads((Path(__file__).resolve().parents[1]/"data/handoffs/catalyst_canvas_stakeholder_handoff.json").read_text())
    payload["relationships"][0]["target_canvas_stakeholder_id"]="missing"
    repo=SQLiteCaseRepository(":memory:"); case=repo.create_case(title="Broken Canvas")
    with pytest.raises(NarrativeRiskValidationError,match="does not reference"): repo.import_catalyst_canvas_stakeholders(case["case_id"],payload)
    repo.close()
