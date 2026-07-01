#!/usr/bin/env python3
"""Generate Catalyst Narrative Risk JSON and Markdown briefs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import build_narrative_risk_record


def markdown_brief(record: dict) -> str:
    lines = [
        "# Catalyst Narrative Risk Brief",
        "",
        f"**Claim:** {record.get('claim', '')}",
        "",
        f"**Risk score:** {record['risk_score']} / 100",
        f"**Risk level:** {record['risk_level']}",
        "",
        "## Decision note",
        "",
        record["decision_note"],
        "",
        "## Flags",
        "",
    ]
    for flag in record.get("flags", []):
        lines.append(f"- {flag}")
    lines += ["", "## Review actions", ""]
    for action in record.get("review_actions", []):
        lines.append(f"- {action}")
    lines += ["", "## Method", "", record.get("method", "transparent heuristic scoring"), ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--json-out", required=True, help="Output JSON file")
    parser.add_argument("--markdown-out", required=False, help="Output Markdown file")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    record = build_narrative_risk_record(payload)

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
