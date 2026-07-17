#!/usr/bin/env python3
"""Compare canonical Python results with the browser engine fixture output."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.service import NarrativeRiskValidationError, VERSION, score_narrative_risk


def main() -> int:
    fixture = json.loads((ROOT / "tests" / "fixtures" / "scoring-parity.json").read_text(encoding="utf-8"))
    completed = subprocess.run(
        ["node", str(ROOT / "scripts" / "browser_fixture_dump.js")],
        check=True,
        capture_output=True,
        text=True,
    )
    browser = json.loads(completed.stdout)
    if browser["version"] != VERSION or fixture["contract_version"] != VERSION:
        raise AssertionError("contract version mismatch")

    browser_valid = {item["name"]: item["result"] for item in browser["valid"]}
    for case in fixture["valid"]:
        python_result = score_narrative_risk(**case["payload"])
        if python_result != browser_valid[case["name"]]:
            raise AssertionError(f"runtime mismatch: {case['name']}")

    browser_invalid = {item["name"]: item["message"] for item in browser["invalid"]}
    for case in fixture["invalid"]:
        try:
            score_narrative_risk(**case["payload"])
        except NarrativeRiskValidationError as exc:
            python_message = str(exc)
        else:
            raise AssertionError(f"Python accepted invalid fixture: {case['name']}")
        if python_message != browser_invalid[case["name"]]:
            raise AssertionError(f"invalid-input mismatch: {case['name']}")

    print(f"Cross-runtime parity passed: {len(fixture['valid'])} valid and {len(fixture['invalid'])} invalid fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
