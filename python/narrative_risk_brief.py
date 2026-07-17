#!/usr/bin/env python3
"""Generate validated Catalyst Narrative Risk v1.1.0 JSON and Markdown briefs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import NarrativeRiskValidationError, build_narrative_risk_record


def markdown_brief(record: dict) -> str:
    normalized = record["normalized_input"]
    calculations = record["calculations"]
    interpretation = record["interpretation"]
    lines = [
        "# Catalyst Narrative Risk Brief",
        "",
        f"**Claim:** {normalized['claim']}",
        "",
        f"**Risk score:** {calculations['risk_score']} / 100",
        f"**Risk level:** {interpretation['risk_level']}",
        f"**Record ID:** {record['identifiers']['record_id']}",
        f"**Case ID:** {record['identifiers']['case_id']}",
        f"**Method:** {record['identifiers']['method_id']} @ {record['method_snapshot']['method_version']}",
        f"**Schema:** {record['identifiers']['schema_id']}",
        f"**Method snapshot SHA-256:** `{record['method_snapshot_sha256']}`",
        "",
        "## Decision note",
        "",
        interpretation["decision_note"],
        "",
        "## Flags",
        "",
    ]
    lines.extend(f"- {flag}" for flag in interpretation["flags"])
    lines += ["", "## Review actions", ""]
    lines.extend(f"- {action}" for action in interpretation["review_actions"])
    lines += ["", "## Component calculations", ""]
    for key, component in calculations["components"].items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {component['input_value']} → {component['weight']} points")
    lines += [
        "",
        "## Human decision",
        "",
        f"- Status: {record['human_decision']['status']}",
        f"- Disposition: {record['human_decision']['disposition']}",
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
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
