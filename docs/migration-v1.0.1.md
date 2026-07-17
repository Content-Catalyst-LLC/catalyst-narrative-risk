# Migrating v1.0.1 Records

Only records that validate against the retained v1.0.1 schema are accepted.

Migration:

- Reuses the original normalized `inputs`
- Preserves `generated_at`
- Preserves the original risk score and level
- Creates deterministic UUID-based record and case identifiers from the legacy record digest
- Embeds the v1.3.0 method snapshot and an empty evidence ledger
- Adds migration warnings
- Sets human disposition to `undecided`

The old `review_status` field indicates review completion only. It cannot establish approval, rejection, or approval conditions.
