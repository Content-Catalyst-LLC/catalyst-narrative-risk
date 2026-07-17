# Canonical contract

Catalyst Narrative Risk v1.3.0 uses a five-layer record:

1. `normalized_input`
2. `evidence_ledger`
3. `calculations`
4. `interpretation`
5. `human_decision`

The record identifies the contract, method, record schema, input schema, and evidence-ledger schema. The complete method snapshot is embedded and hashed.

## Reproducibility digests

- `method_snapshot_sha256`
- `reproducibility.canonical_input_sha256`
- `reproducibility.evidence_ledger_sha256`
- `reproducibility.record_payload_sha256`

The record-payload digest covers the entire record before the reproducibility object is attached. Exact reproduction rebuilds claims, sources, evidence, relationships, calculations, interpretation, and governance fields from the normalized input, ledger input representation, stored method, IDs, timestamp, and human decision.

## Compatibility

The release supports deterministic migration from schema-valid v1.0.1 and v1.1.0 records. Archived schemas remain in `schemas/archive/` and are part of the release contract.
