# Catalyst Narrative Risk

**Current release: v1.0.1 — Scoring Parity and Release Integrity**

Catalyst Narrative Risk is an open-source module for separating claims, sources, evidence strength, uncertainty, timeline pressure, stakeholder pressure, and interpretation risk.

It is part of the Sustainable Catalyst platform. The module does not decide whether a claim is true automatically. It makes the review path visible: what is being claimed, what supports it, what remains uncertain, how quickly the narrative is changing, and what should be reviewed before the claim is used in public strategy, reporting, research, or decision support.

## What the module does

- Scores narrative risk using transparent, versioned heuristics.
- Produces equivalent analytical results in Python and browser JavaScript.
- Separates evidence strength from stakeholder and timeline pressure.
- Flags claims that may be under-sourced, overconfident, volatile, or consequential.
- Produces schema-validated JSON and Markdown review briefs.
- Provides a client-side WordPress demo for public exploration.
- Rejects missing claims, malformed source counts, and unsupported fields explicitly.
- Includes canonical parity fixtures, tests, schemas, sample inputs, outputs, and release contracts.

## v1.0.1 integrity repair

The original browser scorer used JavaScript truthy fallbacks. Valid zero weights for primary sources, strong evidence, and completed review were therefore replaced by fallback values. v1.0.1 extracts a reusable browser engine and requires exact parity with the Python engine across valid, invalid, and score-boundary fixtures.

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

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Generate the sample brief:

```bash
python python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out outputs/sample_narrative_risk_output.json \
  --markdown-out outputs/sample_narrative_risk_output.md
```

## Release validation

Install development dependencies and run the full cross-runtime release suite:

```bash
python -m pip install -r requirements-dev.txt
bash scripts/release_check.sh
```

The suite covers Python 3 tests, schema validation, version consistency, JSON syntax, JavaScript syntax, browser fixtures, direct Python–JavaScript parity, CLI generation, and WordPress PHP syntax.

## Repository structure

```text
narrative_risk/                         Canonical scoring, validation, and isolated legacy shim
python/narrative_risk_brief.py          Validated CLI generator
schemas/                                Strict JSON Schema for exports
data/                                   Sample input records
outputs/                                Schema-valid example outputs
docs/                                   Methodology, parity, review, and release documentation
tests/fixtures/scoring-parity.json      Shared Python/browser scoring contract
scripts/                                Release, parity, and browser validation tools
wordpress/catalyst-narrative-risk-demo/ WordPress shortcode plugin
.github/workflows/                       Python, Node, and PHP CI validation
release/                                Version-specific release notes
```

## Methodological boundary

Catalyst Narrative Risk is not a fact-checking oracle, legal review, communications approval system, or automatic truth engine. It structures review. Human judgment, source evaluation, and domain expertise remain responsible for final interpretation.
