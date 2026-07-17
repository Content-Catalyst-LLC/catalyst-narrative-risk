# Contributing

Changes to scoring, normalization, flags, actions, thresholds, exports, or validation must preserve the cross-runtime contract.

Before opening a pull request:

```bash
python -m pip install -r requirements-dev.txt
bash scripts/release_check.sh
```

When changing analytical behavior:

1. Update the Python engine and browser engine together.
2. Add or revise a canonical fixture in `tests/fixtures/scoring-parity.json`.
3. Update the JSON Schema when the record contract changes.
4. Update methodology and release documentation.
5. Do not weaken the human-review or truth-verification boundary.

Pull requests must pass Python, Node, PHP, schema, version, CLI, and cross-runtime parity checks.
