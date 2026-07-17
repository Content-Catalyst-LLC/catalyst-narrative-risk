# Canonical Contract

Catalyst Narrative Risk v1.6.0 uses a six-layer canonical record:

1. `normalized_input` — validated inputs and explicit map source material
2. `evidence_ledger` — claims, sources, excerpts, relationships, provenance, citations, and coverage
3. `narrative_map` — typed nodes, structural links, wording variants, comparisons, and advisory diagnostics
4. `calculations` — inspectable weighted heuristic components and score
5. `interpretation` — risk level, flags, decision note, and review actions
6. `human_decision` — reviewer-authored status and disposition, never inferred from the score

The record also embeds the complete method snapshot and stores SHA-256 digests for the method, normalized input, evidence ledger, narrative map, and full record payload.

The scoring algorithm and ledger derivation policy remain unchanged from v1.3.0. Narrative-map diagnostics are advisory and cannot silently change the risk score.

## Workspace governance records

The six-layer analytical record remains immutable. v1.6.0 stores governance around a revision as separate review-template, governance-workflow, review-assignment, and governance-decision records. This separation prevents a heuristic score or prior `human_decision` field from becoming an institutional approval implicitly.
