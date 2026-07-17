# Export specification

## Canonical JSON

The canonical JSON record conforms to `schemas/narrative_risk_record.schema.json` and includes the complete evidence ledger, method snapshot, calculations, interpretation, human decision, and reproducibility digests.

## Markdown brief

`python/narrative_risk_brief.py` can produce a human-readable brief containing record identity, score, claims, evidence relationships, flags, review actions, component calculations, human-decision status, and source list.

## Bibliography

The same command can write a standalone Harvard-style Markdown source list with `--bibliography-out`.

## Evidence-ledger exports

`python/export_evidence_ledger.py` exports:

- `json` — complete ledger object
- `markdown` — claims, sources, and relationship overview
- `csv` — one row per claim-evidence relationship with claim text, excerpt, source, locator, relationship type, and strength

Exports preserve canonical IDs so they can be joined back to the full record.
