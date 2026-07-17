#!/usr/bin/env python3
"""Require exact v1.6.0 record, evidence-ledger, and digest parity across runtimes."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.contracts import canonical_json
from narrative_risk.service import build_narrative_risk_record, verify_record_reproducibility


def main() -> int:
    browser = json.loads(subprocess.run(
        ["node", str(ROOT / "scripts" / "browser_record_dump.js")],
        check=True, capture_output=True, text=True,
    ).stdout)
    payload = json.loads((ROOT / "data" / "sample_narrative_risk_input.json").read_text(encoding="utf-8"))
    python = build_narrative_risk_record(
        payload,
        generated_at="2026-07-17T12:00:00+00:00",
        record_id="urn:uuid:10000000-0000-4000-8000-000000000001",
        case_id="urn:uuid:10000000-0000-4000-8000-000000000002",
        human_decision={
            "status": "reviewed", "disposition": "approved_with_conditions", "reviewer_id": "reviewer-17",
            "reviewer_name": "Review Lead", "reviewed_at": "2026-07-17T13:00:00+00:00",
            "notes": "Use within the measured pilot boundary.",
        },
    )
    if canonical_json(browser) != canonical_json(python):
        for key in python:
            if canonical_json(browser.get(key)) != canonical_json(python.get(key)):
                raise AssertionError(f"cross-runtime record mismatch in {key}")
        raise AssertionError("cross-runtime canonical record mismatch")
    report = verify_record_reproducibility(python)
    checks = ["exact_match", "method_snapshot_hash_match", "canonical_input_hash_match", "evidence_ledger_hash_match", "narrative_map_hash_match", "record_payload_hash_match"]
    if not all(report[key] for key in checks):
        raise AssertionError(f"Python record is not reproducible: {report}")
    print("Cross-runtime canonical record, evidence ledger, narrative map, and digest parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
