#!/usr/bin/env python3
"""Require exact canonical record and SHA-256 parity across Python and JavaScript."""

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
    python = build_narrative_risk_record(
        {
            "claim": "A Montréal climate narrative requires transparent review.",
            "source_type": "official_or_primary", "evidence_strength": "strong", "uncertainty": "low",
            "narrative_volatility": "medium", "stakeholder_pressure": "low", "time_sensitivity": "high",
            "consequences": "high", "review_status": "reviewed", "source_count": 5,
            "method_notes": "Unicode and digest parity fixture.",
        },
        generated_at="2026-07-17T12:00:00+00:00",
        record_id="urn:uuid:10000000-0000-4000-8000-000000000001",
        case_id="urn:uuid:10000000-0000-4000-8000-000000000002",
        human_decision={
            "status": "reviewed", "disposition": "approved_with_conditions", "reviewer_id": "reviewer-17",
            "reviewer_name": "Review Lead", "reviewed_at": "2026-07-17T13:00:00+00:00",
            "notes": "Use with the stated time boundary.",
        },
    )
    if canonical_json(browser) != canonical_json(python):
        for key in python:
            if browser.get(key) != python.get(key):
                raise AssertionError(f"cross-runtime record mismatch in {key}")
        raise AssertionError("cross-runtime canonical record mismatch")
    if not verify_record_reproducibility(python)["exact_match"]:
        raise AssertionError("Python record is not reproducible")
    print("Cross-runtime canonical record and digest parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
