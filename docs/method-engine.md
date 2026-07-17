# Method engine

The transparent heuristic remains a weighted additive method. v1.3.0 adds a versioned ledger policy without changing the boundary between analysis and human judgment.

## Scalar components

The engine calculates source type, evidence strength, uncertainty, narrative volatility, stakeholder pressure, time sensitivity, consequences, review status, and source-count weights. Every component includes its selected value, weight, rationale, and remediation guidance.

## Ledger derivation

When the primary claim has relationships:

- Unique linked sources determine source count.
- The lowest-risk source class among positive linked sources determines source type.
- The strongest positive relationship establishes base evidence strength.
- Fewer than two independent positive source groups cause one strength downgrade.
- Contradictory evidence causes one additional downgrade.

The complete policy is stored in `method_snapshot.ledger_policy`; it is therefore inspectable and reproducible for every record.

## Ledger interpretation

The method adds review flags and actions for missing primary-claim relationships, contradictory evidence, dependent or duplicated sources, stale sources, and indirect-only evidence.

These outputs are prompts for review, not automated truth or approval decisions.
