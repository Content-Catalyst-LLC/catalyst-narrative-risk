# Scoring parity contract

Catalyst Narrative Risk v1.0.1 uses the same normalized input contract and scoring behavior in Python and browser JavaScript.

The canonical fixture matrix is stored at:

```text
tests/fixtures/scoring-parity.json
```

It covers:

- valid zero-weight selections;
- default inputs;
- high-risk inputs;
- the Low/Medium score boundary at 39 and 40;
- fallback normalization;
- missing and malformed inputs.

Run the browser contract and direct runtime comparison with:

```bash
node scripts/test_browser_engine.js
python scripts/cross_runtime_parity.py
```

Generated timestamps are excluded from scoring comparisons. All analytical fields, normalized inputs, components, flags, actions, and decision notes must be identical.
