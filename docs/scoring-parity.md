# Scoring and ledger parity

The shared fixture matrix contains valid scalar and evidence-ledger cases plus invalid normalization, vocabulary, cross-reference, relationship, and conflict cases.

The release gate runs each fixture through Python and browser JavaScript and compares:

- Success or exact validation message
- Normalized scalar inputs
- Claims, sources, evidence, relationships, coverage, citations, and derived scoring inputs
- Component calculations, risk score, flags, actions, and decision note
- Complete fixed-ID canonical records
- Method, input, evidence-ledger, and record-payload SHA-256 digests

The browser method asset is generated from `methods/transparent-heuristic.v1.2.0.json` and checked for drift.
