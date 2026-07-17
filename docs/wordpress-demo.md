# WordPress demo

Install `wordpress/catalyst-narrative-risk-demo/` and add:

```text
[catalyst_narrative_risk_demo]
```

The demo runs entirely in the browser. Scalar fields can be used alone, or an optional JSON object can supply `claims`, `sources`, `evidence_items`, and `relationships`.

When ledger JSON is supplied, the interface removes manual source type, evidence strength, and source count values before invoking the engine. The engine derives those values from linked evidence and rejects invalid cross-references or controlled vocabularies.

The result panel displays score, component weights, evidence coverage, derived source inputs, source citations, flags, review actions, human-decision state, and complete JSON export.
