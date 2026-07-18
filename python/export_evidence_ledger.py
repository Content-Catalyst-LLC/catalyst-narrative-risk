#!/usr/bin/env python3
"""Export a v2.0.0 evidence ledger as JSON, Markdown, or CSV."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import NarrativeRiskValidationError, validate_narrative_risk_record


def markdown(ledger: dict) -> str:
    lines = ["# Evidence Ledger", "", "## Claims", ""]
    lines.extend(f"- {item['role']} · {item['claim_type']} · {item['text']}" for item in ledger["claims"])
    lines += ["", "## Sources", ""]
    lines.extend(f"- {item['citation']}" for item in ledger["source_list"] or [])
    lines += ["", "## Relationships", ""]
    if not ledger["relationships"]:
        lines.append("- No relationships recorded.")
    else:
        for item in ledger["relationships"]:
            lines.append(f"- {item['relation_type']} · {item['strength']} · {item['claim_id']} ← {item['evidence_id']}")
    lines.append("")
    return "\n".join(lines)


def csv_text(ledger: dict) -> str:
    evidence = {item["evidence_id"]: item for item in ledger["evidence_items"]}
    sources = {item["source_id"]: item for item in ledger["sources"]}
    claims = {item["claim_id"]: item for item in ledger["claims"]}
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["relationship_id","claim_id","claim_text","relation_type","strength","evidence_id","excerpt","source_id","source_title","locator"])
    writer.writeheader()
    for relationship in ledger["relationships"]:
        item = evidence[relationship["evidence_id"]]
        source = sources[item["source_id"]]
        claim = claims[relationship["claim_id"]]
        writer.writerow({
            "relationship_id": relationship["relationship_id"], "claim_id": claim["claim_id"], "claim_text": claim["text"],
            "relation_type": relationship["relation_type"], "strength": relationship["strength"], "evidence_id": item["evidence_id"],
            "excerpt": item["excerpt"], "source_id": source["source_id"], "source_title": source["title"], "locator": item["locator"],
        })
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=["json", "markdown", "csv"], default="json")
    args = parser.parse_args()
    try:
        record = json.loads(Path(args.input).read_text(encoding="utf-8"))
        validate_narrative_risk_record(record)
    except (OSError, json.JSONDecodeError, NarrativeRiskValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    ledger = record["evidence_ledger"]
    if args.format == "json":
        content = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    elif args.format == "markdown":
        content = markdown(ledger)
    else:
        content = csv_text(ledger)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
