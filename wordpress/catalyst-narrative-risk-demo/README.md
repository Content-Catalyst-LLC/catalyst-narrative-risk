# Catalyst Narrative Risk Demo v1.2.0

Install this directory as a WordPress plugin and activate it.

Use:

```text
[catalyst_narrative_risk_demo]
```

The demo runs entirely in the visitor's browser. `narrative-risk-method.js` is generated from the canonical v1.2.0 method JSON. The browser engine produces the same claims, sources, evidence relationships, coverage analysis, citations, layered record, hashes, score, and interpretation as Python.

The optional evidence-ledger JSON field accepts `claims`, `sources`, `evidence_items`, and `relationships`. When relationships are supplied, the source type, evidence strength, and source count used by the heuristic are derived from the ledger.
