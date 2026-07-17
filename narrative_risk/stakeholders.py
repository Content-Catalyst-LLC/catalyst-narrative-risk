"""Stakeholder, incentive, pressure, and consequence intelligence for v1.9.0.

This layer records observable actors and evidence-linked relationships. It does
not infer hidden motives or silently change the canonical analytical score.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Sequence
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from .contracts import (
    STAKEHOLDER_ACTOR_SCHEMA_PATH, STAKEHOLDER_RELATIONSHIP_SCHEMA_PATH,
    STAKEHOLDER_INCENTIVE_SCHEMA_PATH, STAKEHOLDER_PRESSURE_SCHEMA_PATH,
    STAKEHOLDER_CONSEQUENCE_SCHEMA_PATH, STAKEHOLDER_INTELLIGENCE_SCHEMA_PATH,
    CATALYST_CANVAS_STAKEHOLDER_HANDOFF_SCHEMA_PATH, sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError

VERSION = "1.9.0"
ACTOR_TYPES = {"individual","community","organization","company","government","regulator","funder","media","research_institution","advocacy_group","public","other"}
INFLUENCE_LEVELS = {"low","medium","high","critical"}
STANCES = {"supportive","neutral","opposed","mixed","unknown"}
DISCLOSURE_STATUSES = {"not_required","disclosed","partially_disclosed","not_disclosed","unknown"}
RELATIONSHIP_TYPES = {"funds","employs","governs","regulates","represents","advises","partners_with","competes_with","depends_on","supplies","influences","amplifies","contests","benefits_from","harmed_by","other"}
RELATIONSHIP_DIRECTIONS = {"directed","mutual","undirected"}
RELATIONSHIP_STRENGTHS = {"low","medium","high","critical","unknown"}
INCENTIVE_TYPES = {"financial","political","reputational","legal","social","operational","mission","career","ideological","other"}
INCENTIVE_ALIGNMENTS = {"aligned","mixed","opposed","unknown"}
CONFLICT_STATUSES = {"none","potential","confirmed","managed","unknown"}
PRESSURE_TYPES = {"financial","political","reputational","legal","social","operational","deadline","funding","media","public","other"}
PRESSURE_HORIZONS = {"immediate","short_term","medium_term","long_term","ongoing"}
PRESSURE_STATUSES = {"active","historical","anticipated","disputed"}
IMPACT_TYPES = {"financial","reputational","legal","operational","social","environmental","political","health","safety","rights","other"}
IMPACT_DIRECTIONS = {"benefit","harm","mixed","unknown"}
SEVERITIES = {"low","moderate","high","critical"}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, field: str, *, required: bool=False, maximum: int=20000) -> str:
    if value is None: value = ""
    if not isinstance(value, str): raise NarrativeRiskValidationError(f"{field} must be a string")
    value=value.strip()
    if required and not value: raise NarrativeRiskValidationError(f"{field} is required")
    if len(value)>maximum: raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return value


def _choice(value: Any, field: str, allowed: Iterable[str], default: str) -> str:
    if value is None or value=="": return default
    if not isinstance(value,str): raise NarrativeRiskValidationError(f"{field} must be a string")
    value=value.strip().lower()
    if value not in allowed: raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(sorted(allowed))}")
    return value


def _strings(value: Any, field: str, *, maximum: int=100, item_maximum: int=1000) -> list[str]:
    if value is None: return []
    if not isinstance(value, Sequence) or isinstance(value,(str,bytes)): raise NarrativeRiskValidationError(f"{field} must be an array of strings")
    out=[]; seen=set()
    for i,item in enumerate(value):
        clean=_text(item,f"{field}[{i}]",required=True,maximum=item_maximum)
        if clean not in seen: out.append(clean); seen.add(clean)
    if len(out)>maximum: raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum} values")
    return out


def urn(value: str|None, field: str, *, material: Mapping[str,Any]|None=None) -> str:
    if value is None:
        if material is not None: return f"urn:uuid:{uuid5(NAMESPACE_URL, sha256_digest(material))}"
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value,str) or not value.startswith("urn:uuid:"): raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try: UUID(value[9:])
    except Exception as exc: raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def _validate(label: str, value: Mapping[str,Any], schema) -> None:
    try: validate_against_schema(value,schema)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"): raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


def normalize_actor(payload: Mapping[str,Any], *, case_id: str, created_at: str|None=None) -> Dict[str,Any]:
    if not isinstance(payload,Mapping): raise NarrativeRiskValidationError("stakeholder actor must be a JSON object")
    name=_text(payload.get("name"),"name",required=True,maximum=500)
    actor={
      "actor_id":urn(payload.get("actor_id"),"actor_id",material={"case_id":case_id,"name":name,"actor_type":payload.get("actor_type","organization")}),
      "case_id":urn(case_id,"case_id"),"name":name,"actor_type":_choice(payload.get("actor_type"),"actor_type",ACTOR_TYPES,"organization"),
      "description":_text(payload.get("description"),"description"),"interests":_strings(payload.get("interests"),"interests"),
      "influence":_choice(payload.get("influence"),"influence",INFLUENCE_LEVELS,"medium"),"stance":_choice(payload.get("stance"),"stance",STANCES,"unknown"),
      "disclosure_status":_choice(payload.get("disclosure_status"),"disclosure_status",DISCLOSURE_STATUSES,"unknown"),
      "external_id":_text(payload.get("external_id"),"external_id",maximum=500) or None,"notes":_text(payload.get("notes"),"notes"),
      "created_at":created_at or payload.get("created_at") or iso_now(),"created_by":_text(payload.get("created_by"),"created_by",maximum=500) or None,
    }
    _validate("stakeholder actor",actor,STAKEHOLDER_ACTOR_SCHEMA_PATH); return actor


def normalize_relationship(payload: Mapping[str,Any], *, case_id: str, created_at: str|None=None) -> Dict[str,Any]:
    source=urn(payload.get("source_actor_id"),"source_actor_id"); target=urn(payload.get("target_actor_id"),"target_actor_id")
    if source==target: raise NarrativeRiskValidationError("stakeholder relationship must connect two different actors")
    item={"relationship_id":urn(payload.get("relationship_id"),"relationship_id",material={"case_id":case_id,"source":source,"target":target,"type":payload.get("relationship_type","other")}),
      "case_id":urn(case_id,"case_id"),"source_actor_id":source,"target_actor_id":target,
      "relationship_type":_choice(payload.get("relationship_type"),"relationship_type",RELATIONSHIP_TYPES,"other"),
      "direction":_choice(payload.get("direction"),"direction",RELATIONSHIP_DIRECTIONS,"directed"),
      "strength":_choice(payload.get("strength"),"strength",RELATIONSHIP_STRENGTHS,"unknown"),
      "description":_text(payload.get("description"),"description"),"evidence_ids":_strings(payload.get("evidence_ids"),"evidence_ids",item_maximum=500),
      "created_at":created_at or payload.get("created_at") or iso_now(),"created_by":_text(payload.get("created_by"),"created_by",maximum=500) or None}
    _validate("stakeholder relationship",item,STAKEHOLDER_RELATIONSHIP_SCHEMA_PATH); return item


def normalize_incentive(payload: Mapping[str,Any], *, case_id: str, created_at: str|None=None) -> Dict[str,Any]:
    actor_id=urn(payload.get("actor_id"),"actor_id"); conflict=_choice(payload.get("conflict_status"),"conflict_status",CONFLICT_STATUSES,"unknown"); evidence=_strings(payload.get("evidence_ids"),"evidence_ids",item_maximum=500)
    if conflict=="confirmed" and not evidence: raise NarrativeRiskValidationError("confirmed conflict_status requires at least one evidence_id")
    item={"incentive_id":urn(payload.get("incentive_id"),"incentive_id",material={"case_id":case_id,"actor_id":actor_id,"type":payload.get("incentive_type","other"),"description":payload.get("description","")}),
      "case_id":urn(case_id,"case_id"),"actor_id":actor_id,"incentive_type":_choice(payload.get("incentive_type"),"incentive_type",INCENTIVE_TYPES,"other"),
      "description":_text(payload.get("description"),"description",required=True),"magnitude":_choice(payload.get("magnitude"),"magnitude",INFLUENCE_LEVELS,"medium"),
      "alignment":_choice(payload.get("alignment"),"alignment",INCENTIVE_ALIGNMENTS,"unknown"),"disclosed":bool(payload.get("disclosed",False)),"conflict_status":conflict,
      "evidence_ids":evidence,"created_at":created_at or payload.get("created_at") or iso_now(),"created_by":_text(payload.get("created_by"),"created_by",maximum=500) or None}
    _validate("stakeholder incentive",item,STAKEHOLDER_INCENTIVE_SCHEMA_PATH); return item


def normalize_pressure(payload: Mapping[str,Any], *, case_id: str, created_at: str|None=None) -> Dict[str,Any]:
    actor_id=urn(payload.get("actor_id"),"actor_id"); src=payload.get("source_actor_id")
    item={"pressure_id":urn(payload.get("pressure_id"),"pressure_id",material={"case_id":case_id,"actor_id":actor_id,"type":payload.get("pressure_type","other"),"description":payload.get("description","")}),
      "case_id":urn(case_id,"case_id"),"actor_id":actor_id,"source_actor_id":urn(src,"source_actor_id") if src else None,
      "pressure_type":_choice(payload.get("pressure_type"),"pressure_type",PRESSURE_TYPES,"other"),"description":_text(payload.get("description"),"description",required=True),
      "intensity":_choice(payload.get("intensity"),"intensity",INFLUENCE_LEVELS,"medium"),"time_horizon":_choice(payload.get("time_horizon"),"time_horizon",PRESSURE_HORIZONS,"ongoing"),
      "status":_choice(payload.get("status"),"status",PRESSURE_STATUSES,"active"),"evidence_ids":_strings(payload.get("evidence_ids"),"evidence_ids",item_maximum=500),
      "created_at":created_at or payload.get("created_at") or iso_now(),"created_by":_text(payload.get("created_by"),"created_by",maximum=500) or None}
    _validate("stakeholder pressure",item,STAKEHOLDER_PRESSURE_SCHEMA_PATH); return item


def normalize_consequence(payload: Mapping[str,Any], *, case_id: str, created_at: str|None=None) -> Dict[str,Any]:
    actor_id=urn(payload.get("actor_id"),"actor_id")
    item={"consequence_id":urn(payload.get("consequence_id"),"consequence_id",material={"case_id":case_id,"actor_id":actor_id,"type":payload.get("impact_type","other"),"description":payload.get("description","")}),
      "case_id":urn(case_id,"case_id"),"actor_id":actor_id,"impact_type":_choice(payload.get("impact_type"),"impact_type",IMPACT_TYPES,"other"),
      "direction":_choice(payload.get("direction"),"direction",IMPACT_DIRECTIONS,"unknown"),"severity":_choice(payload.get("severity"),"severity",SEVERITIES,"moderate"),
      "description":_text(payload.get("description"),"description",required=True),"affected_claim_ids":_strings(payload.get("affected_claim_ids"),"affected_claim_ids",item_maximum=500),
      "mitigation":_text(payload.get("mitigation"),"mitigation"),"evidence_ids":_strings(payload.get("evidence_ids"),"evidence_ids",item_maximum=500),
      "created_at":created_at or payload.get("created_at") or iso_now(),"created_by":_text(payload.get("created_by"),"created_by",maximum=500) or None}
    _validate("stakeholder consequence",item,STAKEHOLDER_CONSEQUENCE_SCHEMA_PATH); return item


def build_stakeholder_intelligence(*, case_id: str, actors: Sequence[Mapping[str,Any]], relationships: Sequence[Mapping[str,Any]], incentives: Sequence[Mapping[str,Any]], pressures: Sequence[Mapping[str,Any]], consequences: Sequence[Mapping[str,Any]], generated_at: str|None=None) -> Dict[str,Any]:
    intensity={"low":1,"medium":2,"high":3,"critical":4}; influence=intensity; conflict={"none":0,"managed":1,"potential":2,"confirmed":3,"unknown":1}
    scores={a["actor_id"]:0 for a in actors}; flags=[]
    for a in actors: scores[a["actor_id"]]+=influence[a["influence"]]
    for p in pressures:
        scores[p["actor_id"]]=scores.get(p["actor_id"],0)+intensity[p["intensity"]]
        if p["intensity"] in {"high","critical"} and p["status"] in {"active","anticipated"}: flags.append(f"{p['intensity']}_pressure:{p['pressure_id']}")
    for i in incentives:
        scores[i["actor_id"]]=scores.get(i["actor_id"],0)+conflict[i["conflict_status"]]
        if i["conflict_status"] in {"potential","confirmed"}: flags.append(f"{i['conflict_status']}_conflict:{i['incentive_id']}")
        if not i["disclosed"] and i["magnitude"] in {"high","critical"}: flags.append(f"undisclosed_incentive:{i['incentive_id']}")
    max_score=max(scores.values(),default=0); suggested="low" if max_score<=3 else "medium" if max_score<=5 else "high"
    high_harm=sum(1 for c in consequences if c["direction"] in {"harm","mixed"} and c["severity"] in {"high","critical"})
    if high_harm: flags.append(f"high_consequence_exposure:{high_harm}")
    ranking=sorted(({"actor_id":a["actor_id"],"name":a["name"],"score":scores.get(a["actor_id"],0),"influence":a["influence"],"stance":a["stance"]} for a in actors),key=lambda x:(-x["score"],x["name"].casefold()))
    result={"intelligence_version":VERSION,"case_id":urn(case_id,"case_id"),"generated_at":generated_at or iso_now(),
      "counts":{"actors":len(actors),"relationships":len(relationships),"incentives":len(incentives),"pressures":len(pressures),"consequences":len(consequences)},
      "suggested_stakeholder_pressure":suggested,"maximum_actor_pressure_score":max_score,"flags":sorted(set(flags)),"actor_pressure_ranking":ranking,
      "boundary":"Advisory evidence-linked assessment; does not infer motives or change the canonical score automatically."}
    result["intelligence_sha256"]=sha256_digest(result)
    _validate("stakeholder intelligence",result,STAKEHOLDER_INTELLIGENCE_SCHEMA_PATH); return result


def validate_canvas_handoff(payload: Mapping[str,Any]) -> Dict[str,Any]:
    if not isinstance(payload,Mapping): raise NarrativeRiskValidationError("Catalyst Canvas handoff must be a JSON object")
    _validate("Catalyst Canvas stakeholder handoff",payload,CATALYST_CANVAS_STAKEHOLDER_HANDOFF_SCHEMA_PATH)
    return dict(payload)
