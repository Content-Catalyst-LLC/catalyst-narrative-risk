#!/usr/bin/env python3
"""Migrate a Catalyst Narrative Risk v1.0.1 or v1.1.0 record to v1.3.0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.migrations import migrate_record
from narrative_risk.service import NarrativeRiskValidationError, verify_record_reproducibility


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--migrated-at", help="Fixed ISO 8601 migration time")
    args = parser.parse_args()
    try:
        legacy = json.loads(Path(args.input).read_text(encoding="utf-8"))
        migrated = migrate_record(legacy, migrated_at=args.migrated_at)
        report = verify_record_reproducibility(migrated)
        if not report["exact_match"]:
            raise NarrativeRiskValidationError("migrated record failed reproducibility verification")
    except (OSError, json.JSONDecodeError, NarrativeRiskValidationError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(migrated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
