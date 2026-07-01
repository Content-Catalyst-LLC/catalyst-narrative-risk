# Contributing

Contributions should preserve the Sustainable Catalyst standard: transparent assumptions, traceable claims, readable methods, and reviewable outputs.

## Principles

- Keep scoring logic inspectable and deterministic.
- Do not present heuristic scores as truth verification.
- Keep examples educational and non-sensitive.
- Preserve JSON export compatibility when possible.
- Add tests when changing scoring, flags, or output structure.

## Local checks

```bash
python -m pytest
python python/narrative_risk_brief.py --input data/sample_narrative_risk_input.json --json-out outputs/sample_narrative_risk_output.json --markdown-out outputs/sample_narrative_risk_output.md
```
