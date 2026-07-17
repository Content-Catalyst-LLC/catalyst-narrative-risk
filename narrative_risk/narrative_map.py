"""Claim decomposition, narrative mapping, wording comparison, and review diagnostics."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .contracts import NARRATIVE_MAP_SCHEMA_PATH, sha256_digest, validate_against_schema
from .errors import NarrativeRiskValidationError

MAP_VERSION = "1.4.0"
NODE_TYPES = (
    "factual_claim", "causal_claim", "predictive_claim", "normative_claim",
    "recommendation", "assumption", "context", "unknown",
)
NODE_ROLES = ("primary", "supporting", "context")
CONFIDENCE_LANGUAGE = ("absolute", "confident", "qualified", "tentative", "unknown")
MODALITIES = ("asserts", "suggests", "predicts", "recommends", "questions")
LINK_TYPES = (
    "decomposes_to", "depends_on", "causes", "predicts", "supports", "qualifies",
    "contradicts", "contextualizes", "recommends", "sequence",
)
LINK_STRENGTHS = ("strong", "moderate", "limited", "unclear")
VARIANT_STATUS = ("current", "draft", "preferred", "rejected", "archived")
SEVERITIES = ("low", "medium", "high", "critical")
MAP_ID_RE = re.compile(r"^urn:catalyst:narrative-risk:(node|link|variant|issue):sha256:[0-9a-f]{64}$")

AMBIGUOUS_TERMS = (
    "significant", "substantial", "meaningful", "many", "most", "some", "often",
    "soon", "rapidly", "generally", "typically", "likely", "unlikely", "major",
    "better", "worse", "effective", "successful", "safe", "sustainable",
)
CAUSAL_MARKERS = ("causes", "caused", "leads to", "led to", "results in", "resulted in", "drives", "because", "due to")
PREDICTIVE_MARKERS = ("will", "forecast", "projected", "expected to", "likely to", "is expected", "is projected")
NORMATIVE_MARKERS = ("should", "must", "ought", "need to", "needs to", "required to")
ABSOLUTE_MARKERS = ("always", "never", "certainly", "proves", "guarantees", "without doubt", "will definitely")
UNCERTAINTY_MARKERS = ("may", "might", "could", "appears", "suggests", "approximately", "potentially", "uncertain")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")


def _clean_text(value: Any, field: str, *, required: bool = False, maximum: int = 50000) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    if len(cleaned) > maximum:
        raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return cleaned


def _choice(value: Any, field: str, allowed: Sequence[str], default: str) -> str:
    if value is None or value == "":
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    if cleaned not in allowed:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(allowed)}")
    return cleaned


def _array(value: Any, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise NarrativeRiskValidationError(f"{field} must be an array")
    return value


def _object(value: Any, field: str, allowed: Iterable[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NarrativeRiskValidationError(f"{field} must be a JSON object")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported {field} field(s): {', '.join(unknown)}")
    return value


def _string_list(value: Any, field: str, *, maximum_items: int = 1000) -> list[str]:
    values = _array(value, field)
    if len(values) > maximum_items:
        raise NarrativeRiskValidationError(f"{field} must contain no more than {maximum_items} items")
    output = [_clean_text(item, f"{field}[{index}]", required=True, maximum=1000) for index, item in enumerate(values)]
    if len(output) != len(set(output)):
        raise NarrativeRiskValidationError(f"{field} contains duplicate values")
    return output


def stable_map_id(kind: str, material: Mapping[str, Any]) -> str:
    if kind not in {"node", "link", "variant", "issue"}:
        raise NarrativeRiskValidationError(f"unsupported narrative-map identifier kind: {kind}")
    return f"urn:catalyst:narrative-risk:{kind}:sha256:{sha256_digest(material)}"


def _map_id(value: Any, kind: str, material: Mapping[str, Any], field: str) -> str:
    if value is None or value == "":
        return stable_map_id(kind, material)
    if not isinstance(value, str) or not MAP_ID_RE.fullmatch(value) or f":{kind}:" not in value:
        raise NarrativeRiskValidationError(f"{field} must be a canonical {kind} identifier")
    return value


def _unique(items: Sequence[Mapping[str, Any]], key: str, field: str) -> None:
    values = [item[key] for item in items]
    duplicate = next((value for value, count in Counter(values).items() if count > 1), None)
    if duplicate:
        raise NarrativeRiskValidationError(f"duplicate {field}: {duplicate}")


def _node_type_from_claim_type(value: str) -> str:
    return {
        "factual": "factual_claim", "causal": "causal_claim", "predictive": "predictive_claim",
        "normative": "normative_claim", "recommendation": "recommendation", "interpretive": "unknown",
    }.get(value, "unknown")


def _confidence_from_text(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in ABSOLUTE_MARKERS):
        return "absolute"
    if any(marker in lowered for marker in UNCERTAINTY_MARKERS):
        return "tentative"
    if any(marker in lowered for marker in ("likely", "strongly indicates", "demonstrates")):
        return "confident"
    return "unknown"


def _modality_from_type(node_type: str) -> str:
    if node_type == "predictive_claim":
        return "predicts"
    if node_type in {"recommendation", "normative_claim"}:
        return "recommends"
    return "asserts"


def _normalize_quantity(raw: Any, field: str) -> Dict[str, Any]:
    item = _object(raw, field, {"value", "unit", "context"})
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise NarrativeRiskValidationError(f"{field}.value must be a number or string")
    if isinstance(value, str):
        value = _clean_text(value, f"{field}.value", required=True, maximum=1000)
    return {
        "value": value,
        "unit": _clean_text(item.get("unit", ""), f"{field}.unit", maximum=200),
        "context": _clean_text(item.get("context", ""), f"{field}.context", maximum=5000),
    }


def _normalize_nodes(raw: Any, ledger: Mapping[str, Any]) -> List[Dict[str, Any]]:
    values = _array(raw, "narrative_nodes")
    if not values:
        values = [
            {
                "text": claim["text"],
                "node_type": _node_type_from_claim_type(claim["claim_type"]),
                "role": claim["role"],
                "claim_id": claim["claim_id"],
            }
            for claim in ledger["claims"]
        ]
    allowed = {
        "node_id", "text", "node_type", "role", "claim_id", "parent_node_id",
        "confidence_language", "modality", "entities", "geography", "time_scope",
        "quantities", "baseline", "notes",
    }
    claim_ids = {item["claim_id"] for item in ledger["claims"]}
    output: List[Dict[str, Any]] = []
    for index, raw_node in enumerate(values):
        item = _object(raw_node, f"narrative_nodes[{index}]", allowed)
        text = _clean_text(item.get("text"), f"narrative_nodes[{index}].text", required=True, maximum=20000)
        node_type = _choice(item.get("node_type"), f"narrative_nodes[{index}].node_type", NODE_TYPES, "unknown")
        role = _choice(item.get("role"), f"narrative_nodes[{index}].role", NODE_ROLES, "supporting")
        claim_id = item.get("claim_id")
        if claim_id in (None, ""):
            claim_id = None
        elif not isinstance(claim_id, str) or claim_id not in claim_ids:
            raise NarrativeRiskValidationError(f"narrative_nodes[{index}].claim_id does not reference a normalized claim")
        parent_node_id = item.get("parent_node_id")
        if parent_node_id in (None, ""):
            parent_node_id = None
        elif not isinstance(parent_node_id, str):
            raise NarrativeRiskValidationError(f"narrative_nodes[{index}].parent_node_id must be a string or null")
        quantities = [_normalize_quantity(value, f"narrative_nodes[{index}].quantities[{q_index}]") for q_index, value in enumerate(_array(item.get("quantities"), f"narrative_nodes[{index}].quantities"))]
        material = {"index": index, "text": text, "node_type": node_type, "role": role, "claim_id": claim_id}
        output.append({
            "node_id": _map_id(item.get("node_id"), "node", material, f"narrative_nodes[{index}].node_id"),
            "text": text,
            "node_type": node_type,
            "role": role,
            "claim_id": claim_id,
            "parent_node_id": parent_node_id,
            "confidence_language": _choice(item.get("confidence_language"), f"narrative_nodes[{index}].confidence_language", CONFIDENCE_LANGUAGE, _confidence_from_text(text)),
            "modality": _choice(item.get("modality"), f"narrative_nodes[{index}].modality", MODALITIES, _modality_from_type(node_type)),
            "entities": _string_list(item.get("entities"), f"narrative_nodes[{index}].entities"),
            "geography": _string_list(item.get("geography"), f"narrative_nodes[{index}].geography"),
            "time_scope": None if item.get("time_scope") in (None, "") else _clean_text(item.get("time_scope"), f"narrative_nodes[{index}].time_scope", required=True, maximum=2000),
            "quantities": quantities,
            "baseline": None if item.get("baseline") in (None, "") else _clean_text(item.get("baseline"), f"narrative_nodes[{index}].baseline", required=True, maximum=5000),
            "notes": _clean_text(item.get("notes", ""), f"narrative_nodes[{index}].notes", maximum=50000),
        })
    _unique(output, "node_id", "node_id")
    node_ids = {item["node_id"] for item in output}
    for index, item in enumerate(output):
        parent = item["parent_node_id"]
        if parent is not None and parent not in node_ids:
            raise NarrativeRiskValidationError(f"narrative_nodes[{index}].parent_node_id does not reference a normalized node")
        if parent == item["node_id"]:
            raise NarrativeRiskValidationError(f"narrative_nodes[{index}].parent_node_id cannot reference itself")
    if len([item for item in output if item["role"] == "primary"]) != 1:
        raise NarrativeRiskValidationError("narrative_nodes must contain exactly one primary node")
    return output


def _normalize_links(raw: Any, node_ids: set[str]) -> List[Dict[str, Any]]:
    values = _array(raw, "narrative_links")
    output: List[Dict[str, Any]] = []
    allowed = {"link_id", "from_node_id", "to_node_id", "relation_type", "strength", "notes"}
    for index, raw_link in enumerate(values):
        item = _object(raw_link, f"narrative_links[{index}]", allowed)
        from_id = item.get("from_node_id")
        to_id = item.get("to_node_id")
        if not isinstance(from_id, str) or from_id not in node_ids:
            raise NarrativeRiskValidationError(f"narrative_links[{index}].from_node_id does not reference a normalized node")
        if not isinstance(to_id, str) or to_id not in node_ids:
            raise NarrativeRiskValidationError(f"narrative_links[{index}].to_node_id does not reference a normalized node")
        if from_id == to_id:
            raise NarrativeRiskValidationError(f"narrative_links[{index}] cannot link a node to itself")
        relation = _choice(item.get("relation_type"), f"narrative_links[{index}].relation_type", LINK_TYPES, "depends_on")
        strength = _choice(item.get("strength"), f"narrative_links[{index}].strength", LINK_STRENGTHS, "unclear")
        material = {"index": index, "from_node_id": from_id, "to_node_id": to_id, "relation_type": relation, "strength": strength}
        output.append({
            "link_id": _map_id(item.get("link_id"), "link", material, f"narrative_links[{index}].link_id"),
            "from_node_id": from_id,
            "to_node_id": to_id,
            "relation_type": relation,
            "strength": strength,
            "notes": _clean_text(item.get("notes", ""), f"narrative_links[{index}].notes", maximum=50000),
        })
    _unique(output, "link_id", "link_id")
    keys = [(item["from_node_id"], item["to_node_id"], item["relation_type"]) for item in output]
    if len(keys) != len(set(keys)):
        raise NarrativeRiskValidationError("duplicate narrative link")
    return output


def _normalize_variants(raw: Any, claim: str, selected: Any) -> tuple[List[Dict[str, Any]], str]:
    values = _array(raw, "wording_variants")
    if not values:
        values = [{"label": "Current wording", "text": claim, "status": "current"}]
    allowed = {"variant_id", "label", "text", "audience", "status", "notes"}
    output: List[Dict[str, Any]] = []
    for index, raw_variant in enumerate(values):
        item = _object(raw_variant, f"wording_variants[{index}]", allowed)
        text = _clean_text(item.get("text"), f"wording_variants[{index}].text", required=True, maximum=20000)
        label = _clean_text(item.get("label", f"Variant {index + 1}"), f"wording_variants[{index}].label", required=True, maximum=1000)
        status = _choice(item.get("status"), f"wording_variants[{index}].status", VARIANT_STATUS, "draft")
        material = {"index": index, "label": label, "text": text, "status": status}
        output.append({
            "variant_id": _map_id(item.get("variant_id"), "variant", material, f"wording_variants[{index}].variant_id"),
            "label": label,
            "text": text,
            "audience": _clean_text(item.get("audience", ""), f"wording_variants[{index}].audience", maximum=2000),
            "status": status,
            "notes": _clean_text(item.get("notes", ""), f"wording_variants[{index}].notes", maximum=50000),
        })
    _unique(output, "variant_id", "variant_id")
    current = [item for item in output if item["status"] == "current"]
    if len(current) > 1:
        raise NarrativeRiskValidationError("wording_variants may contain at most one current variant")
    selected_id = selected
    if selected_id in (None, ""):
        selected_id = (current[0] if current else output[0])["variant_id"]
    if not isinstance(selected_id, str) or selected_id not in {item["variant_id"] for item in output}:
        raise NarrativeRiskValidationError("selected_variant_id does not reference a normalized wording variant")
    return output, selected_id


def _tokens(text: str) -> list[str]:
    return [token.lower().replace("’", "'") for token in TOKEN_RE.findall(text)]


def _contains(text: str, markers: Sequence[str]) -> list[str]:
    lowered = text.lower()
    return [marker for marker in markers if re.search(r"\b" + re.escape(marker) + r"\b", lowered)]


def _wording_comparisons(variants: Sequence[Mapping[str, Any]], selected_id: str) -> List[Dict[str, Any]]:
    selected = next(item for item in variants if item["variant_id"] == selected_id)
    base_tokens = _tokens(selected["text"])
    base_set = set(base_tokens)
    output = []
    for variant in variants:
        if variant["variant_id"] == selected_id:
            continue
        tokens = _tokens(variant["text"])
        token_set = set(tokens)
        union = base_set | token_set
        similarity = 1.0 if not union else round(len(base_set & token_set) / len(union), 6)
        base_abs = len(_contains(selected["text"], ABSOLUTE_MARKERS))
        other_abs = len(_contains(variant["text"], ABSOLUTE_MARKERS))
        base_unc = len(_contains(selected["text"], UNCERTAINTY_MARKERS))
        other_unc = len(_contains(variant["text"], UNCERTAINTY_MARKERS))
        if other_abs > base_abs and other_unc <= base_unc:
            direction = "higher"
        elif other_abs < base_abs or other_unc > base_unc:
            direction = "lower"
        elif other_abs == base_abs and other_unc == base_unc:
            direction = "same"
        else:
            direction = "mixed"
        output.append({
            "from_variant_id": selected_id,
            "to_variant_id": variant["variant_id"],
            "similarity": similarity,
            "added_terms": sorted(token_set - base_set),
            "removed_terms": sorted(base_set - token_set),
            "absolute_language_delta": other_abs - base_abs,
            "uncertainty_language_delta": other_unc - base_unc,
            "causal_language_delta": len(_contains(variant["text"], CAUSAL_MARKERS)) - len(_contains(selected["text"], CAUSAL_MARKERS)),
            "risk_direction": direction,
        })
    return output


def _issue(code: str, severity: str, node_ids: Sequence[str], message: str, remediation: str) -> Dict[str, Any]:
    material = {"code": code, "severity": severity, "node_ids": list(node_ids), "message": message}
    return {
        "issue_id": stable_map_id("issue", material), "code": code, "severity": severity,
        "node_ids": list(node_ids), "message": message, "remediation": remediation,
    }


def _find_cycles(nodes: Sequence[Mapping[str, Any]], links: Sequence[Mapping[str, Any]]) -> List[List[str]]:
    graph: Dict[str, List[str]] = {item["node_id"]: [] for item in nodes}
    for item in links:
        if item["relation_type"] in {"decomposes_to", "depends_on", "causes", "predicts"}:
            graph[item["from_node_id"]].append(item["to_node_id"])
    cycles: List[List[str]] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: List[str] = []

    def walk(node: str) -> None:
        if node in visiting:
            start = stack.index(node)
            cycle = stack[start:] + [node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visiting.add(node); stack.append(node)
        for target in graph[node]:
            walk(target)
        stack.pop(); visiting.remove(node); visited.add(node)

    for node in graph:
        walk(node)
    return cycles


def _analyze(nodes: Sequence[Mapping[str, Any]], links: Sequence[Mapping[str, Any]], ledger: Mapping[str, Any], uncertainty: str, evidence_strength: str) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    link_types_by_node: Dict[str, set[str]] = {item["node_id"]: set() for item in nodes}
    linked_nodes: set[str] = set()
    for link in links:
        link_types_by_node[link["from_node_id"]].add(link["relation_type"])
        link_types_by_node[link["to_node_id"]].add(link["relation_type"])
        linked_nodes.update({link["from_node_id"], link["to_node_id"]})

    node_analysis = []
    for node in nodes:
        text = node["text"]
        ambiguous = _contains(text, AMBIGUOUS_TERMS)
        causal = _contains(text, CAUSAL_MARKERS)
        predictive = _contains(text, PREDICTIVE_MARKERS)
        normative = _contains(text, NORMATIVE_MARKERS)
        word_count = len(_tokens(text))
        compound_count = text.count(";") + len(re.findall(r"\b(?:and|while|whereas|as well as)\b", text.lower()))
        mismatch = node["confidence_language"] in {"absolute", "confident"} and (uncertainty == "high" or evidence_strength in {"weak", "limited", "unclear"})
        node_analysis.append({
            "node_id": node["node_id"], "word_count": word_count, "ambiguous_terms": ambiguous,
            "causal_markers": causal, "predictive_markers": predictive, "normative_markers": normative,
            "compound_indicator_count": compound_count, "confidence_mismatch": mismatch,
        })
        if ambiguous:
            issues.append(_issue("ambiguous_language", "medium", [node["node_id"]], f"Ambiguous terms require operational definitions: {', '.join(ambiguous)}.", "Replace or define vague terms using measurable criteria, scope, and timeframe."))
        if word_count > 45 or compound_count >= 2:
            issues.append(_issue("compound_or_overbroad_claim", "medium", [node["node_id"]], "The statement combines multiple propositions or exceeds the recommended review length.", "Split the statement into atomic claims and connect them explicitly."))
        if (node["node_type"] == "causal_claim" or causal) and "causes" not in link_types_by_node[node["node_id"]]:
            issues.append(_issue("unsupported_causal_structure", "high", [node["node_id"]], "Causal language is present without an explicit causal relationship in the map.", "Identify the proposed cause and effect as separate nodes and connect them with a causes link."))
        if (node["node_type"] == "predictive_claim" or predictive) and not ({"predicts", "sequence"} & link_types_by_node[node["node_id"]]) and not node["time_scope"]:
            issues.append(_issue("unbounded_prediction", "high", [node["node_id"]], "Predictive language lacks an explicit dependency, sequence, or time horizon.", "Add the forecast horizon, assumptions, and the node or condition on which the prediction depends."))
        if node["quantities"] and not node["baseline"]:
            issues.append(_issue("quantity_without_baseline", "medium", [node["node_id"]], "A quantity is recorded without a comparison baseline.", "Record the baseline, denominator, reference period, and measurement boundary."))
        if mismatch:
            issues.append(_issue("confidence_evidence_mismatch", "high", [node["node_id"]], "The wording is more confident than the recorded uncertainty or evidence strength supports.", "Use qualified language or improve the evidence before publication."))
        if node["role"] != "primary" and node["node_id"] not in linked_nodes and len(nodes) > 1:
            issues.append(_issue("orphan_node", "low", [node["node_id"]], "This narrative node is not connected to the rest of the map.", "Connect the node or remove it from the active narrative."))

    mapped_claim_ids = {item["claim_id"] for item in nodes if item["claim_id"] is not None}
    ledger_claim_ids = {item["claim_id"] for item in ledger["claims"]}
    for claim_id in sorted(ledger_claim_ids - mapped_claim_ids):
        issues.append(_issue("unmapped_claim", "high", [], f"Evidence-ledger claim {claim_id} is not represented in the narrative map.", "Add a narrative node linked to the claim."))
    cycles = _find_cycles(nodes, links)
    for cycle in cycles:
        issues.append(_issue("dependency_cycle", "high", cycle[:-1], "The narrative map contains a circular dependency.", "Break the cycle or document the feedback relationship explicitly as context."))

    severity_counts = {severity: sum(item["severity"] == severity for item in issues) for severity in SEVERITIES}
    if severity_counts["critical"] or severity_counts["high"]:
        status = "needs_review"
    elif issues or len(mapped_claim_ids) < len(ledger_claim_ids):
        status = "partial"
    else:
        status = "complete"
    return {
        "per_node": node_analysis,
        "issues": issues,
        "cycles": cycles,
        "summary": {
            "node_count": len(nodes), "link_count": len(links), "mapped_claim_count": len(mapped_claim_ids & ledger_claim_ids),
            "unmapped_claim_count": len(ledger_claim_ids - mapped_claim_ids), "issue_count": len(issues),
            "severity_counts": severity_counts, "map_status": status, "review_ready": status == "complete",
        },
    }


def build_narrative_map(
    payload: Mapping[str, Any], *, narrative_claim: str, evidence_ledger: Mapping[str, Any],
    uncertainty: str, evidence_strength: str,
) -> Dict[str, Any]:
    nodes = _normalize_nodes(payload.get("narrative_nodes"), evidence_ledger)
    links = _normalize_links(payload.get("narrative_links"), {item["node_id"] for item in nodes})
    variants, selected_id = _normalize_variants(payload.get("wording_variants"), narrative_claim, payload.get("selected_variant_id"))
    analysis = _analyze(nodes, links, evidence_ledger, uncertainty, evidence_strength)
    narrative_map = {
        "map_version": MAP_VERSION,
        "primary_node_id": next(item["node_id"] for item in nodes if item["role"] == "primary"),
        "selected_variant_id": selected_id,
        "nodes": nodes,
        "links": links,
        "wording_variants": variants,
        "wording_comparisons": _wording_comparisons(variants, selected_id),
        "analysis": analysis,
    }
    try:
        validate_against_schema(narrative_map, NARRATIVE_MAP_SCHEMA_PATH)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid narrative map: {exc.message}") from exc
        raise
    return narrative_map


def narrative_map_interpretation(narrative_map: Mapping[str, Any]) -> Dict[str, List[str]]:
    flags: List[str] = []
    actions: List[str] = []
    for issue in narrative_map["analysis"]["issues"]:
        if issue["severity"] in {"high", "critical"} and issue["message"] not in flags:
            flags.append(issue["message"])
        if issue["remediation"] not in actions:
            actions.append(issue["remediation"])
    return {"flags": flags, "actions": actions}


def narrative_map_input_from_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    narrative_map = record["narrative_map"]
    return {
        "narrative_nodes": deepcopy(narrative_map["nodes"]),
        "narrative_links": deepcopy(narrative_map["links"]),
        "wording_variants": deepcopy(narrative_map["wording_variants"]),
        "selected_variant_id": narrative_map["selected_variant_id"],
    }
