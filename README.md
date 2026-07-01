# Catalyst Narrative Risk

Catalyst Narrative Risk is an open-source module for separating claims, sources, evidence strength, uncertainty, timeline pressure, stakeholder pressure, and interpretation risk.

It is part of the Sustainable Catalyst platform. The purpose is not to decide whether a claim is true automatically. The purpose is to make the review path visible: what is being claimed, what supports it, what is uncertain, how quickly the narrative is changing, and what should be reviewed before the claim is used in public-facing strategy, reporting, research, or decision support.

## What the module does

- Scores narrative risk using transparent heuristics.
- Separates evidence strength from stakeholder pressure.
- Flags claims that may be under-sourced, overconfident, time-sensitive, volatile, or consequential.
- Produces JSON and Markdown review briefs.
- Provides a browser-based WordPress demo for public exploration.
- Includes tests, schemas, sample inputs, example outputs, and documentation.

## WordPress demo

The WordPress plugin lives in:

```text
wordpress/catalyst-narrative-risk-demo/
```

Shortcode:

```text
[catalyst_narrative_risk_demo]
```

The demo is client-side. It does not submit visitor inputs to Sustainable Catalyst. It generates a structured narrative-risk record in the browser for exploratory use.

## Python usage

Run the sample brief generator:

```bash
python python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out outputs/sample_narrative_risk_output.json \
  --markdown-out outputs/sample_narrative_risk_output.md
```

Run tests:

```bash
python -m pytest
```

## Repository structure

```text
narrative_risk/                     Core scoring and brief logic
python/narrative_risk_brief.py       CLI generator
schemas/                             JSON schema for exports
data/                                Sample input records
outputs/                             Example generated outputs
docs/                                Methodology, export, review, and demo docs
wordpress/catalyst-narrative-risk-demo/  WordPress shortcode plugin
tests/                               Lightweight pytest tests
.github/workflows/                   CI validation
```

## Methodological boundary

Catalyst Narrative Risk is not a fact-checking oracle, legal review, communications approval system, or automatic truth engine. It helps structure review. Human judgment, source evaluation, and domain expertise remain responsible for final interpretation.
