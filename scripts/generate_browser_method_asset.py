#!/usr/bin/env python3
"""Generate or verify the browser method-snapshot asset from canonical JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "methods" / "transparent-heuristic.v1.2.0.json"
TARGET = ROOT / "wordpress" / "catalyst-narrative-risk-demo" / "assets" / "narrative-risk-method.js"


def render() -> str:
    method = json.loads(SOURCE.read_text(encoding="utf-8"))
    payload = json.dumps(method, ensure_ascii=False, separators=(",", ":"))
    return f"""(function (root, factory) {{\n  'use strict';\n  const method = factory();\n  if (typeof module === 'object' && module.exports) module.exports = method;\n  if (root) root.CatalystNarrativeRiskMethodV120 = method;\n}})(typeof globalThis !== 'undefined' ? globalThis : this, function () {{\n  'use strict';\n  return {payload};\n}});\n"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != expected:
            print("Browser method asset is not synchronized with canonical method JSON.", file=sys.stderr)
            return 1
        print("Browser method asset matches canonical method JSON.")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
