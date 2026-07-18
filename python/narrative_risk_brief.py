#!/usr/bin/env python3
"""Generate validated Catalyst Narrative Risk v1.10.0 JSON, Markdown, and bibliography exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import NarrativeRiskValidationError, build_narrative_risk_record


def bibliography_text(record: dict) -> str:
    lines = ["# Source List", ""]
    source_list = record["evidence_ledger"]["source_list"]
    if not source_list:
        lines.append("No item-level sources have been recorded.")
    else:
        lines.extend(f"- {item['citation']}" for item in source_list)
    lines.append("")
    return "\n".join(lines)


def markdown_brief(record: dict) -> str:
    normalized = record["normalized_input"]
    calculations = record["calculations"]
    interpretation = record["interpretation"]
    ledger = record["evidence_ledger"]
    coverage = ledger["coverage"]["overall"]
    narrative_map = record["narrative_map"]
    map_summary = narrative_map["analysis"]["summary"]
    lines = [
        "# Catalyst Narrative Risk Brief",
        "",
        f"**Primary claim:** {normalized['claim']}",
        "",
        f"**Risk score:** {calculations['risk_score']} / 100",
        f"**Risk level:** {interpretation['risk_level']}",
        f"**Coverage:** {coverage['coverage_status']}",
        f"**Sources / evidence / relationships:** {coverage['source_count']} / {coverage['evidence_count']} / {coverage['relationship_count']}",
        f"**Independent source groups:** {coverage['independent_source_count']}",
        f"**Narrative map:** {map_summary['map_status']} · {map_summary['node_count']} nodes · {map_summary['link_count']} links · {map_summary['issue_count']} issues",
        f"**Record ID:** {record['identifiers']['record_id']}",
        f"**Case ID:** {record['identifiers']['case_id']}",
        f"**Method:** {record['identifiers']['method_id']} @ {record['method_snapshot']['method_version']}",
        f"**Schema:** {record['identifiers']['schema_id']}",
        f"**Evidence ledger schema:** {record['identifiers']['ledger_schema_id']}",
        f"**Narrative map schema:** {record['identifiers']['narrative_map_schema_id']}",
        f"**Method snapshot SHA-256:** `{record['method_snapshot_sha256']}`",
        "",
        "## Decision note",
        "",
        interpretation["decision_note"],
        "",
        "## Claims",
        "",
    ]
    for claim in ledger["claims"]:
        lines.append(f"- **{claim['role']} · {claim['claim_type']}:** {claim['text']} (`{claim['claim_id']}`)")
    lines += ["", "## Evidence relationships", ""]
    if not ledger["relationships"]:
        lines.append("- No item-level evidence relationships have been recorded.")
    else:
        evidence_by_id = {item["evidence_id"]: item for item in ledger["evidence_items"]}
        source_by_id = {item["source_id"]: item for item in ledger["sources"]}
        claim_by_id = {item["claim_id"]: item for item in ledger["claims"]}
        for relationship in ledger["relationships"]:
            evidence = evidence_by_id[relationship["evidence_id"]]
            source = source_by_id[evidence["source_id"]]
            claim = claim_by_id[relationship["claim_id"]]
            lines.append(
                f"- **{relationship['relation_type']} · {relationship['strength']}:** "
                f"“{evidence['excerpt']}” — {source['title']} → {claim['text']}"
            )
    lines += ["", "## Narrative map", ""]
    for node in narrative_map["nodes"]:
        lines.append(f"- **{node['role']} · {node['node_type']} · {node['confidence_language']}:** {node['text']}")
    lines += ["", "### Narrative relationships", ""]
    node_by_id = {item["node_id"]: item for item in narrative_map["nodes"]}
    if not narrative_map["links"]:
        lines.append("- No narrative relationships recorded.")
    else:
        for link in narrative_map["links"]:
            lines.append(
                f"- **{link['relation_type']} · {link['strength']}:** "
                f"{node_by_id[link['from_node_id']]['text']} → {node_by_id[link['to_node_id']]['text']}"
            )
    lines += ["", "### Narrative diagnostics", ""]
    if not narrative_map["analysis"]["issues"]:
        lines.append("- No structural narrative issues detected by the advisory rules.")
    else:
        for issue in narrative_map["analysis"]["issues"]:
            lines.append(f"- **{issue['severity']} · {issue['code']}:** {issue['message']} {issue['remediation']}")
    lines += ["", "## Flags", ""]
    lines.extend(f"- {flag}" for flag in interpretation["flags"])
    lines += ["", "## Review actions", ""]
    lines.extend(f"- {action}" for action in interpretation["review_actions"])
    lines += ["", "## Component calculations", ""]
    for key, component in calculations["components"].items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {component['input_value']} → {component['weight']} points")
    lines += [
        "", "## Human decision", "",
        f"- Status: {record['human_decision']['status']}",
        f"- Disposition: {record['human_decision']['disposition']}",
        "", "## Source List", "",
    ]
    if ledger["source_list"]:
        lines.extend(f"- {item['citation']}" for item in ledger["source_list"])
    else:
        lines.append("No item-level sources have been recorded.")
    lines += [
        "",
        "The heuristic interpretation is advisory. Approval or rejection must be recorded separately by a human reviewer.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--json-out", required=True, help="Output JSON file")
    parser.add_argument("--markdown-out", help="Output Markdown file")
    parser.add_argument("--bibliography-out", help="Output Markdown source list")
    parser.add_argument("--generated-at", help="Fixed ISO 8601 generation time")
    parser.add_argument("--record-id", help="Fixed urn:uuid record identifier")
    parser.add_argument("--case-id", help="Fixed urn:uuid case identifier")
    args = parser.parse_args()

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        record = build_narrative_risk_record(
            payload,
            generated_at=args.generated_at,
            record_id=args.record_id,
            case_id=args.case_id,
        )
    except (OSError, json.JSONDecodeError, NarrativeRiskValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_out:
        md_path = Path(args.markdown_out)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(markdown_brief(record), encoding="utf-8")
    if args.bibliography_out:
        bibliography_path = Path(args.bibliography_out)
        bibliography_path.parent.mkdir(parents=True, exist_ok=True)
        bibliography_path.write_text(bibliography_text(record), encoding="utf-8")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
