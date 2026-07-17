# Migrating v1.1.0 records

The v1.2.0 migrator validates the archived v1.1.0 schema before migration.

It preserves:

- Record and case identifiers
- Generated timestamp
- Normalized scalar inputs
- Risk score and risk level
- Human decision state, reviewer metadata, and notes

It adds:

- v1.2.0 contract, schema, method, and ledger identifiers
- A deterministic primary claim derived from the original claim text
- An empty item-level source and evidence ledger
- Method, normalized-input, evidence-ledger, and record-payload hashes
- Explicit migration warnings

The migrator does not invent sources, excerpts, or evidence relationships from the former scalar source count or evidence-strength values. Those values remain as fallback analytical inputs until reviewers populate the ledger.
