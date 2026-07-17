# Catalyst Narrative Risk WordPress Package v1.3.0

The plugin provides two shortcodes:

```text
[catalyst_narrative_risk_demo]
[catalyst_narrative_risk_workspace]
```

The demo builds a canonical analytical record with claims, sources, evidence relationships, scoring, interpretation, and a separate human decision.

The workspace stores cases, immutable revisions, review comments, search state, and archive state in the visitor's browser. It exports and imports v1.3.0 checksummed case bundles. Institutional deployment should connect the interface to the SQLite-backed REST API rather than treating browser storage as shared persistence.

`narrative-risk-method.js` is generated from the canonical v1.3.0 method JSON. The browser engine produces the same evidence ledger, score, canonical record, and SHA-256 digests as Python.
