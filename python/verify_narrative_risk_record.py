#!/usr/bin/env python3
"""Verify and exactly reproduce a Catalyst Narrative Risk v1.3.0 record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import NarrativeRiskValidationError, verify_record_reproducibility

CHECKS = ["exact_match", "method_snapshot_hash_match", "canonical_input_hash_match", "evidence_ledger_hash_match", "record_payload_hash_match"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        record = json.loads(Path(args.input).read_text(encoding="utf-8"))
        report = verify_record_reproducibility(record)
    except (OSError, json.JSONDecodeError, NarrativeRiskValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if all(report[key] for key in CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
