"""Claims, sources, evidence, provenance, citations, and coverage for v1.3.0."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import urlparse

from .contracts import LEDGER_SCHEMA_PATH, sha256_digest, validate_against_schema
from .errors import NarrativeRiskValidationError

LEDGER_VERSION = "1.3.0"
CLAIM_TYPES = ("factual", "causal", "predictive", "normative", "recommendation", "interpretive")
CLAIM_ROLES = ("primary", "supporting", "context")
EVIDENCE_TYPES = ("quote", "data", "finding", "observation", "method", "context")
RELATION_TYPES = ("support", "qualify", "contradict", "contextualize", "unresolved")
DIRECTNESS_VALUES = ("direct", "indirect", "mixed", "unknown")
FRESHNESS_VALUES = ("current", "aging", "stale", "unknown")
ACQUISITION_METHODS = ("manual", "knowledge_library", "catalyst_data", "api", "document_import", "other")
IDENTIFIER_SCHEMES = ("doi", "isbn", "issn", "url", "handle", "ark", "catalog", "other")
STRENGTH_VALUES = ("strong", "moderate", "limited", "weak", "unclear")
SOURCE_TYPES = (
    "official_or_primary", "peer_reviewed_or_audited", "reputable_secondary",
    "internal_unreviewed", "single_report_or_media", "social_or_anecdotal", "unknown",
)
LEDGER_ID_RE = re.compile(r"^urn:catalyst:narrative-risk:(claim|source|evidence|relationship):sha256:[0-9a-f]{64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _clean_text(value: Any, field: str, *, required: bool = False, maximum: int | None = None) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    if maximum is not None and len(cleaned) > maximum:
        raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return cleaned


def _choice(value: Any, field: str, allowed: Sequence[str], default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    if cleaned not in allowed:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(allowed)}")
    return cleaned


def _nullable_text(value: Any, field: str, maximum: int = 5000) -> str | None:
    if value is None or value == "":
        return None
    return _clean_text(value, field, required=True, maximum=maximum)


def _datetime_or_none(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string or null") from exc
    if parsed.tzinfo is None:
        raise NarrativeRiskValidationError(f"{field} must include a timezone")
    return value


def _url_or_none(value: Any, field: str) -> str | None:
    cleaned = _nullable_text(value, field)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise NarrativeRiskValidationError(f"{field} must be an absolute http or https URL")
    return cleaned


def _year_or_none(value: Any, field: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise NarrativeRiskValidationError(f"{field} must be an integer or null")
    if value < -10000 or value > 9999:
        raise NarrativeRiskValidationError(f"{field} must be between -10000 and 9999")
    return value


def stable_ledger_id(kind: str, material: Mapping[str, Any]) -> str:
    if kind not in {"claim", "source", "evidence", "relationship"}:
        raise NarrativeRiskValidationError(f"unsupported ledger identifier kind: {kind}")
    return f"urn:catalyst:narrative-risk:{kind}:sha256:{sha256_digest(material)}"


def _ledger_id(value: Any, kind: str, material: Mapping[str, Any], field: str) -> str:
    if value is None or value == "":
        return stable_ledger_id(kind, material)
    if not isinstance(value, str) or not LEDGER_ID_RE.fullmatch(value) or f":{kind}:" not in value:
        raise NarrativeRiskValidationError(f"{field} must be a canonical {kind} identifier")
    return value


def _object(value: Any, field: str, allowed: Iterable[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NarrativeRiskValidationError(f"{field} must be a JSON object")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported {field} field(s): {', '.join(unknown)}")
    return value


def _array(value: Any, field: str) -> List[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise NarrativeRiskValidationError(f"{field} must be an array")
    return value


def _unique(items: Sequence[Mapping[str, Any]], key: str, field: str) -> None:
    values = [item[key] for item in items]
    duplicate = next((value for value, count in Counter(values).items() if count > 1), None)
    if duplicate:
        raise NarrativeRiskValidationError(f"duplicate {field}: {duplicate}")


def _normalize_claims(raw: Any, narrative_claim: str) -> List[Dict[str, Any]]:
    values = _array(raw, "claims")
    if not values:
        values = [{"text": narrative_claim, "claim_type": "factual", "role": "primary", "notes": ""}]
    claims: List[Dict[str, Any]] = []
    allowed = {"claim_id", "text", "claim_type", "role", "notes"}
    for index, raw_claim in enumerate(values):
        item = _object(raw_claim, f"claims[{index}]", allowed)
        text = _clean_text(item.get("text"), f"claims[{index}].text", required=True, maximum=20000)
        claim_type = _choice(item.get("claim_type"), f"claims[{index}].claim_type", CLAIM_TYPES, "factual")
        default_role = "primary" if index == 0 else "supporting"
        role = _choice(item.get("role"), f"claims[{index}].role", CLAIM_ROLES, default_role)
        notes = _clean_text(item.get("notes", ""), f"claims[{index}].notes", maximum=50000)
        material = {"index": index, "text": text, "claim_type": claim_type, "role": role}
        claims.append({
            "claim_id": _ledger_id(item.get("claim_id"), "claim", material, f"claims[{index}].claim_id"),
            "text": text,
            "claim_type": claim_type,
            "role": role,
            "notes": notes,
        })
    _unique(claims, "claim_id", "claim_id")
    primary = [item for item in claims if item["role"] == "primary"]
    if len(primary) != 1:
        raise NarrativeRiskValidationError("claims must contain exactly one primary claim")
    if primary[0]["text"] != narrative_claim:
        raise NarrativeRiskValidationError("claim must exactly match the primary claim text")
    return claims


def _normalize_identifiers(raw: Any, field: str) -> List[Dict[str, str]]:
    values = _array(raw, field)
    output = []
    for index, raw_identifier in enumerate(values):
        item = _object(raw_identifier, f"{field}[{index}]", {"scheme", "value"})
        output.append({
            "scheme": _choice(item.get("scheme"), f"{field}[{index}].scheme", IDENTIFIER_SCHEMES, "other"),
            "value": _clean_text(item.get("value"), f"{field}[{index}].value", required=True, maximum=5000),
        })
    output.sort(key=lambda item: (item["scheme"], item["value"]))
    pairs = [(item["scheme"], item["value"]) for item in output]
    if len(pairs) != len(set(pairs)):
        raise NarrativeRiskValidationError(f"{field} contains duplicate identifiers")
    return output


def _normalize_provenance(raw: Any, field: str) -> Dict[str, Any]:
    if raw is None:
        raw = {}
    item = _object(raw, field, {"acquisition_method", "imported_from", "imported_at", "content_sha256"})
    content_hash = item.get("content_sha256")
    if content_hash in (None, ""):
        content_hash = None
    elif not isinstance(content_hash, str) or not HEX64_RE.fullmatch(content_hash):
        raise NarrativeRiskValidationError(f"{field}.content_sha256 must be a lowercase SHA-256 digest or null")
    return {
        "acquisition_method": _choice(item.get("acquisition_method"), f"{field}.acquisition_method", ACQUISITION_METHODS, "manual"),
        "imported_from": _nullable_text(item.get("imported_from"), f"{field}.imported_from"),
        "imported_at": _datetime_or_none(item.get("imported_at"), f"{field}.imported_at"),
        "content_sha256": content_hash,
    }


def _normalize_sources(raw: Any) -> List[Dict[str, Any]]:
    values = _array(raw, "sources")
    sources: List[Dict[str, Any]] = []
    allowed = {
        "source_id", "title", "source_type", "creators", "publisher", "published_year", "url",
        "accessed_at", "identifiers", "independence_group", "duplicate_of_source_id", "directness",
        "freshness", "provenance", "notes",
    }
    for index, raw_source in enumerate(values):
        item = _object(raw_source, f"sources[{index}]", allowed)
        creators_raw = _array(item.get("creators"), f"sources[{index}].creators")
        creators = [_clean_text(value, f"sources[{index}].creators", required=True, maximum=1000) for value in creators_raw]
        identifiers = _normalize_identifiers(item.get("identifiers"), f"sources[{index}].identifiers")
        title = _clean_text(item.get("title"), f"sources[{index}].title", required=True, maximum=20000)
        source_type = _choice(item.get("source_type"), f"sources[{index}].source_type", SOURCE_TYPES, "unknown")
        publisher = _clean_text(item.get("publisher", ""), f"sources[{index}].publisher", maximum=5000)
        published_year = _year_or_none(item.get("published_year"), f"sources[{index}].published_year")
        url = _url_or_none(item.get("url"), f"sources[{index}].url")
        accessed_at = _datetime_or_none(item.get("accessed_at"), f"sources[{index}].accessed_at")
        directness = _choice(item.get("directness"), f"sources[{index}].directness", DIRECTNESS_VALUES, "unknown")
        freshness = _choice(item.get("freshness"), f"sources[{index}].freshness", FRESHNESS_VALUES, "unknown")
        provenance = _normalize_provenance(item.get("provenance"), f"sources[{index}].provenance")
        notes = _clean_text(item.get("notes", ""), f"sources[{index}].notes", maximum=50000)
        material = {
            "index": index, "title": title, "source_type": source_type, "creators": creators,
            "publisher": publisher, "published_year": published_year, "url": url,
            "identifiers": identifiers,
        }
        source_id = _ledger_id(item.get("source_id"), "source", material, f"sources[{index}].source_id")
        duplicate = item.get("duplicate_of_source_id")
        if duplicate in (None, ""):
            duplicate = None
        elif not isinstance(duplicate, str) or not LEDGER_ID_RE.fullmatch(duplicate) or ":source:" not in duplicate:
            raise NarrativeRiskValidationError(f"sources[{index}].duplicate_of_source_id must be a canonical source identifier or null")
        independence_group = _nullable_text(item.get("independence_group"), f"sources[{index}].independence_group", 1000)
        sources.append({
            "source_id": source_id, "title": title, "source_type": source_type, "creators": creators,
            "publisher": publisher, "published_year": published_year, "url": url, "accessed_at": accessed_at,
            "identifiers": identifiers, "independence_group": independence_group or source_id,
            "duplicate_of_source_id": duplicate, "directness": directness, "freshness": freshness,
            "provenance": provenance, "notes": notes,
        })
    _unique(sources, "source_id", "source_id")
    by_id = {item["source_id"]: item for item in sources}
    for item in sources:
        duplicate = item["duplicate_of_source_id"]
        if duplicate is None:
            continue
        if duplicate == item["source_id"]:
            raise NarrativeRiskValidationError("a source cannot duplicate itself")
        if duplicate not in by_id:
            raise NarrativeRiskValidationError(f"duplicate source reference does not exist: {duplicate}")
        # An omitted/default independence group follows the original source.
        if item["independence_group"] == item["source_id"]:
            item["independence_group"] = by_id[duplicate]["independence_group"]
    return sources


def _normalize_evidence(raw: Any, source_ids: set[str]) -> List[Dict[str, Any]]:
    values = _array(raw, "evidence_items")
    output: List[Dict[str, Any]] = []
    allowed = {"evidence_id", "source_id", "evidence_type", "excerpt", "locator", "captured_at", "notes"}
    for index, raw_evidence in enumerate(values):
        item = _object(raw_evidence, f"evidence_items[{index}]", allowed)
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or source_id not in source_ids:
            raise NarrativeRiskValidationError(f"evidence_items[{index}].source_id does not reference a normalized source")
        evidence_type = _choice(item.get("evidence_type"), f"evidence_items[{index}].evidence_type", EVIDENCE_TYPES, "finding")
        excerpt = _clean_text(item.get("excerpt"), f"evidence_items[{index}].excerpt", required=True, maximum=200000)
        locator = _clean_text(item.get("locator", ""), f"evidence_items[{index}].locator", maximum=5000)
        captured_at = _datetime_or_none(item.get("captured_at"), f"evidence_items[{index}].captured_at")
        notes = _clean_text(item.get("notes", ""), f"evidence_items[{index}].notes", maximum=50000)
        excerpt_hash = sha256_digest(excerpt)
        material = {"index": index, "source_id": source_id, "evidence_type": evidence_type, "excerpt_sha256": excerpt_hash, "locator": locator}
        output.append({
            "evidence_id": _ledger_id(item.get("evidence_id"), "evidence", material, f"evidence_items[{index}].evidence_id"),
            "source_id": source_id, "evidence_type": evidence_type, "excerpt": excerpt, "locator": locator,
            "captured_at": captured_at, "excerpt_sha256": excerpt_hash, "notes": notes,
        })
    _unique(output, "evidence_id", "evidence_id")
    return output


def _normalize_relationships(raw: Any, claim_ids: set[str], evidence_ids: set[str]) -> List[Dict[str, Any]]:
    values = _array(raw, "relationships")
    output: List[Dict[str, Any]] = []
    allowed = {"relationship_id", "claim_id", "evidence_id", "relation_type", "strength", "notes"}
    for index, raw_relationship in enumerate(values):
        item = _object(raw_relationship, f"relationships[{index}]", allowed)
        claim_id = item.get("claim_id")
        evidence_id = item.get("evidence_id")
        if not isinstance(claim_id, str) or claim_id not in claim_ids:
            raise NarrativeRiskValidationError(f"relationships[{index}].claim_id does not reference a normalized claim")
        if not isinstance(evidence_id, str) or evidence_id not in evidence_ids:
            raise NarrativeRiskValidationError(f"relationships[{index}].evidence_id does not reference normalized evidence")
        relation_type = _choice(item.get("relation_type"), f"relationships[{index}].relation_type", RELATION_TYPES, "unresolved")
        strength = _choice(item.get("strength"), f"relationships[{index}].strength", STRENGTH_VALUES, "unclear")
        notes = _clean_text(item.get("notes", ""), f"relationships[{index}].notes", maximum=50000)
        material = {"index": index, "claim_id": claim_id, "evidence_id": evidence_id, "relation_type": relation_type, "strength": strength}
        output.append({
            "relationship_id": _ledger_id(item.get("relationship_id"), "relationship", material, f"relationships[{index}].relationship_id"),
            "claim_id": claim_id, "evidence_id": evidence_id, "relation_type": relation_type,
            "strength": strength, "notes": notes,
        })
    _unique(output, "relationship_id", "relationship_id")
    pairs = [(item["claim_id"], item["evidence_id"], item["relation_type"], item["strength"]) for item in output]
    if len(pairs) != len(set(pairs)):
        raise NarrativeRiskValidationError("duplicate claim-evidence relationship")
    return output


def _citation_author(creators: Sequence[str]) -> str:
    if not creators:
        return "Unknown author"
    if len(creators) == 1:
        return creators[0]
    if len(creators) == 2:
        return f"{creators[0]} and {creators[1]}"
    return f"{creators[0]} et al."


def harvard_citation(source: Mapping[str, Any]) -> str:
    author = _citation_author(source["creators"])
    year = str(source["published_year"]) if source["published_year"] is not None else "n.d."
    text = f"{author} ({year}) {source['title']}."
    if source["publisher"]:
        text += f" {source['publisher']}."
    if source["url"]:
        text += f" Available at: {source['url']}"
        if source["accessed_at"]:
            text += f" (Accessed: {source['accessed_at'][:10]})"
        text += "."
    return text


def _citation_key(source: Mapping[str, Any]) -> str:
    if source["creators"]:
        token = source["creators"][0].split()[-1]
    else:
        token = "Unknown"
    token = re.sub(r"[^A-Za-z0-9]+", "", token) or "Source"
    year = source["published_year"] if source["published_year"] is not None else "nd"
    return f"{token}{year}-{source['source_id'][-8:]}"


def _strength_rank(value: str, order: Sequence[str]) -> int:
    return order.index(value)


def _downgrade(value: str, steps: int, order: Sequence[str]) -> str:
    return order[max(0, _strength_rank(value, order) - steps)]


def _claim_coverage(
    claim_id: str,
    relationships: Sequence[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, Any]],
    method: Mapping[str, Any],
) -> Dict[str, Any]:
    related = [item for item in relationships if item["claim_id"] == claim_id]
    counts = {kind: 0 for kind in RELATION_TYPES}
    for item in related:
        counts[item["relation_type"]] += 1
    evidence_ids = {item["evidence_id"] for item in related}
    source_ids = {evidence_by_id[evidence_id]["source_id"] for evidence_id in evidence_ids}
    groups = {source_by_id[source_id]["independence_group"] for source_id in source_ids}
    positive_types = set(method["ledger_policy"]["positive_relation_types"])
    positive = [item for item in related if item["relation_type"] in positive_types]
    order = method["ledger_policy"]["strength_order"]
    positive_strength = max((item["strength"] for item in positive), key=lambda value: _strength_rank(value, order), default="unclear")
    contested = counts["contradict"] > 0
    if contested:
        status = "contested"
    elif not positive:
        status = "none"
    else:
        positive_source_ids = {evidence_by_id[item["evidence_id"]]["source_id"] for item in positive}
        positive_groups = {source_by_id[source_id]["independence_group"] for source_id in positive_source_ids}
        policy = method["ledger_policy"]
        if len(positive_groups) >= policy["substantial_minimum_independent_groups"] and _strength_rank(positive_strength, order) >= _strength_rank(policy["substantial_minimum_strength"], order):
            status = "substantial"
        else:
            status = "partial"
    return {
        "claim_id": claim_id,
        "evidence_count": len(evidence_ids),
        "source_count": len(source_ids),
        "independent_source_count": len(groups),
        "relationship_counts": counts,
        "positive_strength": positive_strength,
        "coverage_status": status,
        "contested": contested,
    }


def _derive_scoring_inputs(
    primary_claim_id: str,
    relationships: Sequence[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, Any]],
    method: Mapping[str, Any],
    fallback: Mapping[str, Any],
) -> Dict[str, Any]:
    primary = [item for item in relationships if item["claim_id"] == primary_claim_id]
    if not primary:
        return {
            "ledger_applied": False,
            "source_type": fallback["source_type"],
            "evidence_strength": fallback["evidence_strength"],
            "source_count": fallback["source_count"],
            "basis": "No primary-claim relationships were recorded; explicit or default scalar scoring inputs were retained.",
        }
    source_ids = {evidence_by_id[item["evidence_id"]]["source_id"] for item in primary}
    positive_types = set(method["ledger_policy"]["positive_relation_types"])
    positive = [item for item in primary if item["relation_type"] in positive_types]
    positive_source_ids = {evidence_by_id[item["evidence_id"]]["source_id"] for item in positive}
    source_type_candidates = positive_source_ids or source_ids
    if source_type_candidates:
        source_type = min(
            (source_by_id[source_id]["source_type"] for source_id in source_type_candidates),
            key=lambda value: (method["weights"]["source_type"][value], value),
        )
    else:
        source_type = "unknown"
    order = method["ledger_policy"]["strength_order"]
    base_strength = max((item["strength"] for item in positive), key=lambda value: _strength_rank(value, order), default="unclear")
    positive_groups = {source_by_id[source_id]["independence_group"] for source_id in positive_source_ids}
    strength = base_strength
    policy = method["ledger_policy"]
    if positive and len(positive_groups) < policy["minimum_independent_groups_for_no_downgrade"]:
        strength = _downgrade(strength, policy["single_group_downgrade_steps"], order)
    if any(item["relation_type"] == "contradict" for item in primary):
        strength = _downgrade(strength, policy["contradiction_downgrade_steps"], order)
    return {
        "ledger_applied": True,
        "source_type": source_type,
        "evidence_strength": strength,
        "source_count": len(source_ids),
        "basis": "Derived from evidence relationships linked to the primary claim using the embedded v1.3.0 ledger policy.",
    }


def build_evidence_ledger(
    payload: Mapping[str, Any],
    *,
    narrative_claim: str,
    method_snapshot: Mapping[str, Any],
    fallback_scoring_inputs: Mapping[str, Any],
) -> Dict[str, Any]:
    claims = _normalize_claims(payload.get("claims"), narrative_claim)
    sources = _normalize_sources(payload.get("sources"))
    evidence = _normalize_evidence(payload.get("evidence_items"), {item["source_id"] for item in sources})
    relationships = _normalize_relationships(
        payload.get("relationships"),
        {item["claim_id"] for item in claims},
        {item["evidence_id"] for item in evidence},
    )
    primary_claim_id = next(item["claim_id"] for item in claims if item["role"] == "primary")
    source_by_id = {item["source_id"]: item for item in sources}
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    per_claim = [
        _claim_coverage(item["claim_id"], relationships, evidence_by_id, source_by_id, method_snapshot)
        for item in claims
    ]
    if any(item["coverage_status"] == "contested" for item in per_claim):
        overall_status = "contested"
    elif all(item["coverage_status"] == "substantial" for item in per_claim):
        overall_status = "substantial"
    elif all(item["coverage_status"] == "none" for item in per_claim):
        overall_status = "none"
    else:
        overall_status = "partial"
    ledger = {
        "ledger_version": LEDGER_VERSION,
        "primary_claim_id": primary_claim_id,
        "claims": claims,
        "sources": sources,
        "evidence_items": evidence,
        "relationships": relationships,
        "coverage": {
            "per_claim": per_claim,
            "overall": {
                "claim_count": len(claims),
                "source_count": len(sources),
                "evidence_count": len(evidence),
                "relationship_count": len(relationships),
                "independent_source_count": len({item["independence_group"] for item in sources}),
                "duplicate_source_count": sum(item["duplicate_of_source_id"] is not None for item in sources),
                "direct_source_count": sum(item["directness"] == "direct" for item in sources),
                "stale_source_count": sum(item["freshness"] == "stale" for item in sources),
                "unsupported_claim_count": sum(item["relationship_counts"]["support"] + item["relationship_counts"]["qualify"] == 0 for item in per_claim),
                "contested_claim_count": sum(item["contested"] for item in per_claim),
                "coverage_status": overall_status,
            },
        },
        "source_list": [
            {"source_id": item["source_id"], "citation_key": _citation_key(item), "citation": harvard_citation(item)}
            for item in sources
        ],
        "derived_scoring_inputs": _derive_scoring_inputs(
            primary_claim_id, relationships, evidence_by_id, source_by_id, method_snapshot, fallback_scoring_inputs
        ),
    }
    try:
        validate_against_schema(ledger, LEDGER_SCHEMA_PATH)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid evidence ledger: {exc.message}") from exc
        raise
    return ledger


def ledger_interpretation(ledger: Mapping[str, Any], method_snapshot: Mapping[str, Any]) -> Dict[str, List[str]]:
    primary = next(item for item in ledger["coverage"]["per_claim"] if item["claim_id"] == ledger["primary_claim_id"])
    overall = ledger["coverage"]["overall"]
    primary_source_ids = {
        next(evidence["source_id"] for evidence in ledger["evidence_items"] if evidence["evidence_id"] == relationship["evidence_id"])
        for relationship in ledger["relationships"] if relationship["claim_id"] == ledger["primary_claim_id"]
    }
    primary_sources = [item for item in ledger["sources"] if item["source_id"] in primary_source_ids]
    texts = method_snapshot["ledger_interpretation"]
    flags: List[str] = []
    actions: List[str] = []
    if sum(primary["relationship_counts"].values()) == 0:
        flags.append(texts["flags"]["no_relationships"])
        actions.append(texts["actions"]["record_relationships"])
    if primary["contested"]:
        flags.append(texts["flags"]["contested"])
        actions.append(texts["actions"]["resolve_contestation"])
    if overall["duplicate_source_count"] > 0 or (primary["source_count"] > primary["independent_source_count"]):
        flags.append(texts["flags"]["dependent_sources"])
        actions.append(texts["actions"]["add_independent_sources"])
    if any(item["freshness"] == "stale" for item in primary_sources):
        flags.append(texts["flags"]["stale_sources"])
        actions.append(texts["actions"]["refresh_stale_sources"])
    if primary_sources and all(item["directness"] in {"indirect", "unknown"} for item in primary_sources):
        flags.append(texts["flags"]["indirect_only"])
        actions.append(texts["actions"]["add_direct_evidence"])
    return {"flags": flags, "actions": actions}


def ledger_input_from_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Reconstruct the input-side ledger fields from a canonical record."""
    ledger = record["evidence_ledger"]
    sources = deepcopy(ledger["sources"])
    evidence_items = deepcopy(ledger["evidence_items"])
    for item in evidence_items:
        item.pop("excerpt_sha256", None)
    return {
        "claims": deepcopy(ledger["claims"]),
        "sources": sources,
        "evidence_items": evidence_items,
        "relationships": deepcopy(ledger["relationships"]),
    }
