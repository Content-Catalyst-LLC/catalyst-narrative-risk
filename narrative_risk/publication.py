"""Governance-aware briefings, publication packages, public embeds, API credentials, and platform handoffs for v2.0.0."""
from __future__ import annotations

from base64 import b64encode
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from html import escape
import csv
import io
import json
import re
import secrets
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID, uuid4

from .contracts import (
    API_KEY_SCHEMA_PATH, BRIEFING_SCHEMA_PATH, PLATFORM_HANDOFF_SCHEMA_PATH,
    PUBLICATION_PACKAGE_SCHEMA_PATH, PUBLIC_EMBED_SCHEMA_PATH,
    canonical_json, current_method_snapshot, sha256_digest, validate_against_schema,
)
from .errors import NarrativeRiskValidationError

VERSION = "2.0.0"
AUDIENCES = {"internal", "executive", "technical", "public", "regulatory", "media"}
CLASSIFICATIONS = {"internal", "confidential", "restricted", "public"}
FORMATS = {"json", "markdown", "html", "pdf", "csv", "jsonld"}
PACKAGE_STATUSES = {"draft", "ready", "published", "revoked", "superseded"}
EMBED_STATUSES = {"active", "disabled", "expired", "revoked"}
API_SCOPES = {"records:read", "cases:read", "cases:write", "publication:read", "publication:write", "embeds:read", "embeds:write", "handoffs:write", "admin"}
PLATFORM_TARGETS = {"knowledge_library", "research_librarian", "site_intelligence", "catalyst_data", "catalyst_canvas", "decision_studio", "external"}
SECTION_NAMES = ("executive_summary", "claim", "risk_summary", "evidence_summary", "narrative_summary", "governance_summary", "disclosures", "citations", "reassessment")
MEDIA_TYPES = {"json":"application/json","markdown":"text/markdown","html":"text/html","pdf":"application/pdf","csv":"text/csv","jsonld":"application/ld+json"}
EXTENSIONS = {"json":"json","markdown":"md","html":"html","pdf":"pdf","csv":"csv","jsonld":"jsonld"}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_datetime(value: str | None, field: str, *, required: bool = False) -> str | None:
    if value in (None, ""):
        if required:
            raise NarrativeRiskValidationError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string") from exc
    if parsed.tzinfo is None:
        raise NarrativeRiskValidationError(f"{field} must include a timezone")
    return value


def urn(value: str | None, field: str) -> str:
    if value is None:
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except (ValueError, AttributeError) as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def choice(value: Any, field: str, allowed: Iterable[str], default: str | None = None) -> str:
    if value in (None, ""):
        if default is None:
            raise NarrativeRiskValidationError(f"{field} is required")
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    allowed_set = set(allowed)
    if cleaned not in allowed_set:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(sorted(allowed_set))}")
    return cleaned


def text(value: Any, field: str, *, required: bool = False, maximum: int = 50000) -> str:
    if value is None: value = ""
    if not isinstance(value, str): raise NarrativeRiskValidationError(f"{field} must be a string")
    result = value.strip()
    if required and not result: raise NarrativeRiskValidationError(f"{field} is required")
    if len(result) > maximum: raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return result


def string_list(value: Any, field: str, *, maximum: int = 200) -> list[str]:
    if value is None: return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NarrativeRiskValidationError(f"{field} must be an array of strings")
    output=[]; seen=set()
    for index,item in enumerate(value):
        cleaned=text(item,f"{field}[{index}]",required=True,maximum=5000)
        if cleaned.casefold() not in seen:
            output.append(cleaned); seen.add(cleaned.casefold())
    if len(output)>maximum: raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum} values")
    return output


def schema_validate(label: str, value: Mapping[str, Any], path) -> None:
    try: validate_against_schema(value, path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


def slugify(value: str) -> str:
    slug=re.sub(r"[^a-z0-9]+","-",value.lower()).strip("-")
    if not slug: raise NarrativeRiskValidationError("slug must contain at least one letter or number")
    return slug[:120]


def _latest_final_decision(governance: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not governance: return None
    decisions=governance.get("governance_decisions", [])
    return next((item for item in reversed(decisions) if item.get("stage")=="final"), None)


def _publication_readiness(classification: str, governance: Mapping[str, Any] | None) -> tuple[str,bool,list[str],list[str],str|None,str|None]:
    final=_latest_final_decision(governance)
    restrictions=list(final.get("publication_restrictions",[])) if final else []
    disclosures=list(final.get("disclosures",[])) if final else []
    valid_until=final.get("valid_until") if final else None
    reassessment_at=final.get("reassessment_at") if final else None
    if classification != "public":
        return ("ready" if governance and governance.get("status")=="approved" else "not_assessed", False, restrictions, disclosures, valid_until, reassessment_at)
    if not governance or not governance.get("publication_allowed"):
        return ("blocked", False, restrictions, disclosures, valid_until, reassessment_at)
    conditional={"attribution_required","disclosure_required"}
    return ("conditional" if set(restrictions)&conditional or disclosures else "ready", True, restrictions, disclosures, valid_until, reassessment_at)


def build_briefing(*, case: Mapping[str,Any], revision: Mapping[str,Any], governance: Mapping[str,Any]|None=None,
                   audience: str="internal", classification: str="internal", title: str|None=None,
                   generated_at: str|None=None, generated_by: str|None=None, briefing_id: str|None=None) -> dict[str,Any]:
    audience=choice(audience,"audience",AUDIENCES,"internal")
    classification=choice(classification,"classification",CLASSIFICATIONS,"internal")
    timestamp=validate_datetime(generated_at,"generated_at") or iso_now()
    record=revision.get("record")
    if not isinstance(record,Mapping): raise NarrativeRiskValidationError("revision.record is required")
    readiness,public_safe,restrictions,disclosures,valid_until,reassessment_at=_publication_readiness(classification,governance)
    if classification=="public" and not public_safe:
        raise NarrativeRiskValidationError("public briefing requires a current governance approval with no blocking publication restriction")
    ledger=record["evidence_ledger"]; narrative=record["narrative_map"]
    overall=ledger["coverage"]["overall"]
    redactions=[]
    if classification=="public":
        redactions=list(current_method_snapshot().get("publication_policy",{}).get("redacted_private_fields",[]))
    governance_summary={
        "status":governance.get("status") if governance else "not_started",
        "final_disposition":governance.get("final_disposition") if governance else None,
        "publication_allowed":bool(governance and governance.get("publication_allowed")),
        "conditions":list((_latest_final_decision(governance) or {}).get("conditions",[])),
        "required_wording":list((_latest_final_decision(governance) or {}).get("required_wording",[])),
        "publication_restrictions":restrictions,
    }
    sections={
        "executive_summary": f"{case.get('title','Narrative review')}: {record['interpretation']['decision_note']}",
        "claim": record["normalized_input"]["claim"],
        "risk_summary":{"score":record["calculations"]["risk_score"],"level":record["interpretation"]["risk_level"],"flags":list(record["interpretation"]["flags"]),"review_actions":list(record["interpretation"]["review_actions"])},
        "evidence_summary":{"coverage_status":overall["coverage_status"],"claim_count":overall["claim_count"],"source_count":overall["source_count"],"independent_source_count":overall["independent_source_count"],"evidence_count":overall["evidence_count"],"contested_claim_count":overall["contested_claim_count"],"stale_source_count":overall.get("stale_source_count",0)},
        "narrative_summary":{"node_count":len(narrative.get("narrative_nodes",[])),"link_count":len(narrative.get("narrative_links",[])),"diagnostic_count":len(narrative.get("diagnostics",[])),"diagnostics":deepcopy(narrative.get("diagnostics",[]))},
        "governance_summary":governance_summary,
        "disclosures":disclosures,
        "citations":[item.get("citation","") for item in ledger.get("source_list",[]) if item.get("citation")],
        "reassessment":{"valid_until":valid_until,"reassessment_at":reassessment_at},
    }
    briefing={
        "briefing_id":urn(briefing_id,"briefing_id"),"case_id":case["case_id"],"revision_id":revision["revision_id"],"record_id":revision["record_id"],
        "audience":audience,"classification":classification,"title":text(title or case.get("title"),"title",required=True,maximum=500),
        "generated_at":timestamp,"generated_by":text(generated_by,"generated_by",maximum=500) or None,
        "public_safe":public_safe,"publication_readiness":readiness,"redactions":redactions,"sections":sections,
        "disclosures":disclosures,"publication_restrictions":restrictions,"valid_until":valid_until,"reassessment_at":reassessment_at,
        "source_record_sha256":revision["record_sha256"],
    }
    briefing["briefing_sha256"]=sha256_digest(briefing)
    schema_validate("briefing",briefing,BRIEFING_SCHEMA_PATH)
    return briefing


def briefing_markdown(briefing: Mapping[str,Any]) -> str:
    s=briefing["sections"]; r=s["risk_summary"]; e=s["evidence_summary"]; g=s["governance_summary"]
    lines=[f"# {briefing['title']}","",s["executive_summary"],"","## Claim",s["claim"],"","## Narrative risk",f"**Score:** {r['score']} · **Level:** {r['level']}",""]
    if r["flags"]: lines += ["### Flags"]+[f"- {x}" for x in r["flags"]]+[""]
    lines += ["## Evidence",f"Coverage: {e['coverage_status']}; {e['source_count']} sources; {e['independent_source_count']} independent sources; {e['evidence_count']} evidence items.","","## Governance",f"Status: {g['status']}; final disposition: {g['final_disposition'] or 'none'}; publication allowed: {'yes' if g['publication_allowed'] else 'no'}.",""]
    if briefing["disclosures"]: lines += ["## Disclosures"]+[f"- {x}" for x in briefing["disclosures"]]+[""]
    if s["citations"]: lines += ["## Sources"]+[f"- {x}" for x in s["citations"]]+[""]
    lines += ["## Reassessment",f"Valid until: {briefing.get('valid_until') or 'not set'}",f"Reassess at: {briefing.get('reassessment_at') or 'not set'}",""]
    return "\n".join(lines)


def briefing_html(briefing: Mapping[str,Any]) -> str:
    md=briefing_markdown(briefing)
    chunks=[]
    for line in md.splitlines():
        if line.startswith("# "): chunks.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "): chunks.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("### "): chunks.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("- "): chunks.append(f"<li>{escape(line[2:])}</li>")
        elif line: chunks.append(f"<p>{escape(line)}</p>")
    body="\n".join(chunks)
    return f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\"><title>{escape(briefing['title'])}</title><style>body{{font:16px/1.55 system-ui;max-width:850px;margin:3rem auto;padding:0 1rem}}h1,h2,h3{{line-height:1.2}}li{{margin:.3rem 0}}</style></head><body>{body}</body></html>"


def briefing_csv(briefing: Mapping[str,Any]) -> str:
    output=io.StringIO(); writer=csv.writer(output,lineterminator="\n")
    writer.writerow(["field","value"])
    s=briefing["sections"]
    for key,value in [("briefing_id",briefing["briefing_id"]),("case_id",briefing["case_id"]),("title",briefing["title"]),("claim",s["claim"]),("risk_score",s["risk_summary"]["score"]),("risk_level",s["risk_summary"]["level"]),("evidence_coverage",s["evidence_summary"]["coverage_status"]),("source_count",s["evidence_summary"]["source_count"]),("publication_readiness",briefing["publication_readiness"]),("generated_at",briefing["generated_at"])]: writer.writerow([key,value])
    return output.getvalue()


def briefing_jsonld(briefing: Mapping[str,Any]) -> str:
    value={"@context":{"schema":"https://schema.org/","cnr":"https://sustainablecatalyst.com/ns/narrative-risk#"},"@type":"schema:Report","@id":briefing["briefing_id"],"schema:name":briefing["title"],"schema:dateCreated":briefing["generated_at"],"schema:about":{"@type":"schema:Claim","schema:text":briefing["sections"]["claim"]},"cnr:riskScore":briefing["sections"]["risk_summary"]["score"],"cnr:riskLevel":briefing["sections"]["risk_summary"]["level"],"cnr:publicationReadiness":briefing["publication_readiness"],"cnr:sourceRecord":briefing["record_id"]}
    return json.dumps(value,ensure_ascii=False,indent=2)+"\n"


def _pdf_escape(value: str) -> str:
    return value.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")


def simple_pdf(text_value: str) -> bytes:
    lines=[]
    for paragraph in text_value.splitlines():
        words=paragraph.encode("latin-1","replace").decode("latin-1").split()
        current=""
        for word in words:
            candidate=(current+" "+word).strip()
            if len(candidate)>92 and current: lines.append(current); current=word
            else: current=candidate
        if current: lines.append(current)
        if not words: lines.append("")
    lines=lines[:55]
    stream="BT /F1 10 Tf 50 760 Td 14 TL " + " ".join(f"({_pdf_escape(line)}) Tj T*" for line in lines) + " ET"
    objects=["1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj","2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj","3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources<< /Font<< /F1 4 0 R >> >> /Contents 5 0 R >>endobj","4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj",f"5 0 obj<< /Length {len(stream.encode('latin-1'))} >>stream\n{stream}\nendstream endobj"]
    out=bytearray(b"%PDF-1.4\n"); offsets=[0]
    for obj in objects: offsets.append(len(out)); out.extend((obj+"\n").encode("latin-1"))
    xref=len(out); out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]: out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def artifact_for_format(briefing: Mapping[str,Any], fmt: str, slug: str) -> dict[str,Any]:
    fmt=choice(fmt,"format",FORMATS)
    if fmt=="json": raw=(json.dumps(briefing,ensure_ascii=False,indent=2)+"\n").encode()
    elif fmt=="markdown": raw=briefing_markdown(briefing).encode()
    elif fmt=="html": raw=briefing_html(briefing).encode()
    elif fmt=="csv": raw=briefing_csv(briefing).encode()
    elif fmt=="jsonld": raw=briefing_jsonld(briefing).encode()
    else: raw=simple_pdf(briefing_markdown(briefing))
    encoding="base64" if fmt=="pdf" else "utf-8"
    content=b64encode(raw).decode() if encoding=="base64" else raw.decode()
    return {"format":fmt,"media_type":MEDIA_TYPES[fmt],"filename":f"{slug}.{EXTENSIONS[fmt]}","content_encoding":encoding,"content":content,"content_sha256":__import__('hashlib').sha256(raw).hexdigest(),"size_bytes":len(raw)}


def build_publication_package(briefing: Mapping[str,Any], *, formats: Sequence[str]|None=None, slug: str|None=None, status: str|None=None, generated_at: str|None=None, generated_by: str|None=None, package_id: str|None=None, package_version: int=1, public_url: str|None=None, idempotency_key: str|None=None) -> dict[str,Any]:
    schema_validate("briefing",briefing,BRIEFING_SCHEMA_PATH)
    selected=[]
    for fmt in (formats or ["json","markdown","html"]):
        normalized=choice(fmt,"formats[]",FORMATS)
        if normalized not in selected: selected.append(normalized)
    if not selected: raise NarrativeRiskValidationError("formats must contain at least one format")
    normalized_slug=slugify(slug or briefing["title"])
    normalized_status=choice(status,"status",PACKAGE_STATUSES,"ready" if briefing["publication_readiness"] in {"ready","conditional"} else "draft")
    if normalized_status in {"ready","published"} and briefing["classification"]=="public" and not briefing["public_safe"]:
        raise NarrativeRiskValidationError("a public package cannot be ready or published unless the briefing is public-safe")
    if isinstance(package_version,bool) or not isinstance(package_version,int) or package_version<1: raise NarrativeRiskValidationError("package_version must be a positive integer")
    package={"package_id":urn(package_id,"package_id"),"case_id":briefing["case_id"],"briefing_id":briefing["briefing_id"],"status":normalized_status,"slug":normalized_slug,"package_version":package_version,"generated_at":validate_datetime(generated_at,"generated_at") or iso_now(),"generated_by":text(generated_by,"generated_by",maximum=500) or None,"classification":briefing["classification"],"public_safe":briefing["public_safe"],"public_url":public_url,"idempotency_key":text(idempotency_key,"idempotency_key",maximum=200) or None,"artifacts":[artifact_for_format(briefing,fmt,normalized_slug) for fmt in selected]}
    package["package_sha256"]=sha256_digest(package)
    schema_validate("publication package",package,PUBLICATION_PACKAGE_SCHEMA_PATH)
    return package


def build_public_embed(package: Mapping[str,Any], *, slug: str|None=None, allowed_origins: Sequence[str]|None=None, theme: str="system", show_sections: Sequence[str]|None=None, expires_at: str|None=None, created_at: str|None=None, embed_id: str|None=None) -> dict[str,Any]:
    schema_validate("publication package",package,PUBLICATION_PACKAGE_SCHEMA_PATH)
    if package["classification"]!="public" or not package["public_safe"] or package["status"] not in {"ready","published"}:
        raise NarrativeRiskValidationError("public embeds require a ready or published public-safe package")
    sections=string_list(show_sections or SECTION_NAMES,"show_sections",maximum=len(SECTION_NAMES))
    unknown=set(sections)-set(SECTION_NAMES)
    if unknown: raise NarrativeRiskValidationError(f"unsupported embed section(s): {', '.join(sorted(unknown))}")
    normalized_slug=slugify(slug or package["slug"])
    origins=string_list(allowed_origins or ["*"],"allowed_origins",maximum=50)
    timestamp=validate_datetime(created_at,"created_at") or iso_now(); expiry=validate_datetime(expires_at,"expires_at")
    status="expired" if expiry and datetime.fromisoformat(expiry.replace('Z','+00:00')) <= datetime.fromisoformat(timestamp.replace('Z','+00:00')) else "active"
    code=f'<iframe src="/narrative-risk/embed/{normalized_slug}" title="Narrative Risk Briefing" loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe>'
    value={"embed_id":urn(embed_id,"embed_id"),"case_id":package["case_id"],"package_id":package["package_id"],"slug":normalized_slug,"status":status,"created_at":timestamp,"expires_at":expiry,"allowed_origins":origins,"theme":choice(theme,"theme",{"light","dark","system"},"system"),"show_sections":sections,"embed_code":code}
    value["embed_sha256"]=sha256_digest(value); schema_validate("public embed",value,PUBLIC_EMBED_SCHEMA_PATH); return value


def create_api_key_record(*, name: str, scopes: Sequence[str], rate_limit_per_minute: int|None=None, expires_at: str|None=None, created_at: str|None=None, created_by: str|None=None, api_key_id: str|None=None) -> tuple[dict[str,Any],str]:
    scope_values=string_list(scopes,"scopes",maximum=len(API_SCOPES)); unknown=set(scope_values)-API_SCOPES
    if unknown: raise NarrativeRiskValidationError(f"unsupported API scope(s): {', '.join(sorted(unknown))}")
    if not scope_values: raise NarrativeRiskValidationError("scopes must contain at least one scope")
    policy=current_method_snapshot().get("publication_policy",{})
    limit=rate_limit_per_minute if rate_limit_per_minute is not None else int(policy.get("default_api_rate_limit_per_minute",60))
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=int(policy.get("maximum_api_rate_limit_per_minute",1000)): raise NarrativeRiskValidationError("rate_limit_per_minute is outside the publication policy")
    secret="cnr_"+secrets.token_urlsafe(32).replace("-","").replace("_","")
    record={"api_key_id":urn(api_key_id,"api_key_id"),"name":text(name,"name",required=True,maximum=500),"key_prefix":secret[:12],"key_sha256":__import__('hashlib').sha256(secret.encode()).hexdigest(),"scopes":scope_values,"status":"active","rate_limit_per_minute":limit,"created_at":validate_datetime(created_at,"created_at") or iso_now(),"expires_at":validate_datetime(expires_at,"expires_at"),"last_used_at":None,"created_by":text(created_by,"created_by",maximum=500) or None}
    schema_validate("API key",record,API_KEY_SCHEMA_PATH); return record,secret


def authorize_api_key(record: Mapping[str,Any], secret: str, required_scope: str, *, at: str|None=None) -> None:
    schema_validate("API key",record,API_KEY_SCHEMA_PATH)
    if __import__('hashlib').sha256(secret.encode()).hexdigest()!=record["key_sha256"]: raise NarrativeRiskValidationError("invalid API key")
    if record["status"]!="active": raise NarrativeRiskValidationError("API key is not active")
    now=datetime.fromisoformat((at or iso_now()).replace('Z','+00:00'))
    if record.get("expires_at") and datetime.fromisoformat(record["expires_at"].replace('Z','+00:00'))<=now: raise NarrativeRiskValidationError("API key has expired")
    if required_scope not in record["scopes"] and "admin" not in record["scopes"]: raise NarrativeRiskValidationError(f"API key lacks required scope: {required_scope}")


def build_platform_handoff(package: Mapping[str,Any], *, target: str, generated_at: str|None=None, external_reference: str|None=None, handoff_id: str|None=None) -> dict[str,Any]:
    schema_validate("publication package",package,PUBLICATION_PACKAGE_SCHEMA_PATH)
    normalized_target=choice(target,"target",PLATFORM_TARGETS)
    payload={"handoff_type":"catalyst_narrative_risk_publication","handoff_version":VERSION,"package_id":package["package_id"],"case_id":package["case_id"],"classification":package["classification"],"public_safe":package["public_safe"],"status":package["status"],"formats":[item["format"] for item in package["artifacts"]],"public_url":package.get("public_url"),"artifact_manifest":[{"format":item["format"],"media_type":item["media_type"],"filename":item["filename"],"content_sha256":item["content_sha256"],"size_bytes":item["size_bytes"]} for item in package["artifacts"]]}
    value={"handoff_id":urn(handoff_id,"handoff_id"),"case_id":package["case_id"],"package_id":package["package_id"],"target":normalized_target,"generated_at":validate_datetime(generated_at,"generated_at") or iso_now(),"external_reference":text(external_reference,"external_reference",maximum=1000) or None,"payload":payload,"package_sha256":package["package_sha256"]}
    value["handoff_sha256"]=sha256_digest(value); schema_validate("platform handoff",value,PLATFORM_HANDOFF_SCHEMA_PATH); return value
