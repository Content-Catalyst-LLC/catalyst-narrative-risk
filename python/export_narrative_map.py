#!/usr/bin/env python3
"""Export a validated v1.4.0 narrative map as JSON, Markdown, or Mermaid."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import NarrativeRiskValidationError, validate_narrative_risk_record


def markdown_text(narrative_map: dict) -> str:
    nodes = {item["node_id"]: item for item in narrative_map["nodes"]}
    lines = [
        "# Narrative Map",
        "",
        f"**Status:** {narrative_map['analysis']['summary']['map_status']}",
        f"**Nodes / links / issues:** {len(nodes)} / {len(narrative_map['links'])} / {len(narrative_map['analysis']['issues'])}",
        "",
        "## Nodes",
        "",
    ]
    for item in narrative_map["nodes"]:
        qualifier = f" · {item['confidence_language']} · {item['modality']}"
        lines.append(f"- **{item['role']} · {item['node_type']}{qualifier}:** {item['text']} (`{item['node_id']}`)")
    lines += ["", "## Relationships", ""]
    if not narrative_map["links"]:
        lines.append("- No narrative relationships recorded.")
    else:
        for item in narrative_map["links"]:
            source = nodes[item["from_node_id"]]["text"]
            target = nodes[item["to_node_id"]]["text"]
            lines.append(f"- **{item['relation_type']} · {item['strength']}:** {source} → {target}")
    lines += ["", "## Wording comparisons", ""]
    if not narrative_map["wording_comparisons"]:
        lines.append("- No alternative wording has been compared.")
    else:
        variants = {item["variant_id"]: item for item in narrative_map["wording_variants"]}
        for item in narrative_map["wording_comparisons"]:
            source = variants[item["from_variant_id"]]["label"]
            target = variants[item["to_variant_id"]]["label"]
            lines.append(
                f"- **{source} → {target}:** risk direction `{item['risk_direction']}`, "
                f"similarity {item['similarity']:.3f}, absolute-language delta {item['absolute_language_delta']}."
            )
    lines += ["", "## Review diagnostics", ""]
    if not narrative_map["analysis"]["issues"]:
        lines.append("- No structural narrative issues detected by the advisory rules.")
    else:
        for item in narrative_map["analysis"]["issues"]:
            lines.append(f"- **{item['severity']} · {item['code']}:** {item['message']} _{item['remediation']}_")
    lines += ["", "Narrative-map diagnostics are advisory. They do not verify truth, infer intent, or approve a claim.", ""]
    return "\n".join(lines)


def _mermaid_id(node_id: str, index: int) -> str:
    return f"N{index}_{re.sub(r'[^A-Za-z0-9_]', '_', node_id[-12:])}"


def _mermaid_label(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', "'").replace("\n", " ")[:180]


def mermaid_text(narrative_map: dict) -> str:
    identifiers = {item["node_id"]: _mermaid_id(item["node_id"], index + 1) for index, item in enumerate(narrative_map["nodes"])}
    lines = ["flowchart TD"]
    for item in narrative_map["nodes"]:
        label = f"{item['node_type']}: {_mermaid_label(item['text'])}"
        lines.append(f'    {identifiers[item["node_id"]]}["{label}"]')
    for item in narrative_map["links"]:
        relation = item["relation_type"].replace("_", " ")
        lines.append(f'    {identifiers[item["from_node_id"]]} -->|{relation}| {identifiers[item["to_node_id"]]}')
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Canonical record JSON")
    parser.add_argument("--output", required=True, help="Output path")
    parser.add_argument("--format", choices=["json", "markdown", "mermaid"], default="json")
    args = parser.parse_args()
    try:
        record = json.loads(Path(args.input).read_text(encoding="utf-8"))
        validate_narrative_risk_record(record)
    except (OSError, json.JSONDecodeError, NarrativeRiskValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    narrative_map = record["narrative_map"]
    if args.format == "json":
        content = json.dumps(narrative_map, indent=2, ensure_ascii=False) + "\n"
    elif args.format == "markdown":
        content = markdown_text(narrative_map)
    else:
        content = mermaid_text(narrative_map)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
