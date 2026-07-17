# Reproducibility

`reproduce_narrative_risk_record()` rebuilds a record from its stored normalized input and method snapshot while preserving record ID, case ID, generated time, human decision, and migration metadata.

`verify_record_reproducibility()` checks:

- Embedded method snapshot SHA-256
- Canonical normalized-input SHA-256
- Record-payload SHA-256
- Exact canonical equality between the stored and reproduced records

The Python and browser implementations are required to produce identical canonical records and digests for the release parity fixture.
