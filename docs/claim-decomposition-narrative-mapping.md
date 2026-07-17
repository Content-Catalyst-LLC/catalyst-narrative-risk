# Claim Decomposition and Narrative Mapping

Catalyst Narrative Risk v1.4.0 adds an advisory structural model beside the evidence ledger. The ledger answers **what evidence relates to a claim**. The narrative map answers **what the narrative is made of and how its statements depend on one another**.

## Node model

Each node has a deterministic identifier, text, type, role, confidence language, modality, optional evidence-ledger claim reference, entities, geography, time scope, quantities, baseline, and notes.

Supported node types are factual claim, causal claim, predictive claim, normative claim, recommendation, assumption, context, and unknown.

A map contains exactly one primary node. Supporting and contextual nodes may be linked to ledger claims or may represent assumptions and framing that do not yet have evidence-ledger claim records.

## Relationship model

Typed links include decomposition, dependency, causation, prediction, support, qualification, contradiction, contextualization, recommendation, and sequence. Links are not evidence relationships. They describe narrative structure and must not be interpreted as proof.

## Wording comparison

Wording variants preserve alternative formulations with status and audience metadata. Deterministic comparison reports include token similarity, added and removed terms, absolute-language change, uncertainty-language change, causal-language change, and an advisory risk direction.

## Advisory diagnostics

The map engine checks for:

- ambiguous language
- compound or overbroad claims
- unsupported causal structure
- unbounded predictions
- quantities without baselines
- confidence that exceeds recorded evidence or uncertainty
- orphan nodes
- evidence-ledger claims missing from the map
- circular narrative dependencies

Diagnostics append flags and review actions but do not alter the weighted risk score.

## Integrity

Every canonical record stores `narrative_map_sha256`. Reproduction rebuilds the map from normalized input, confirms the digest, and requires exact canonical equality across Python and browser runtimes.
