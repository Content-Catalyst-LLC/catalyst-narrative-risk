# Export specification

Catalyst Narrative Risk v1.0.1 exports a JSON object conforming to `schemas/narrative_risk_record.schema.json`.

Required metadata includes:

- `record_type`;
- `generated_at`;
- `method`;
- `method_version`;
- `schema_version`.

The analytical body includes the normalized claim inputs, score, level, component weights, flags, review actions, and decision note.

The CLI validates the record before writing it. Browser scoring is verified against the same canonical fixture matrix, while the generated timestamp remains runtime-specific.
