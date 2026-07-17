# Reproducibility

A v1.2.0 record can be rebuilt exactly from its stored normalized input, evidence ledger, method snapshot, IDs, timestamp, human decision, and optional migration metadata.

Verification checks:

1. The method snapshot matches `method_snapshot_sha256`.
2. The normalized input matches `canonical_input_sha256`.
3. The complete evidence ledger matches `evidence_ledger_sha256`.
4. The pre-reproducibility record payload matches `record_payload_sha256`.
5. A freshly reproduced record is canonically identical to the stored record.

Canonical JSON sorts object keys, preserves list order, uses compact separators, retains Unicode, and normalizes integral floating-point values to integers. Python and JavaScript use the same representation and must produce the same SHA-256 values.
