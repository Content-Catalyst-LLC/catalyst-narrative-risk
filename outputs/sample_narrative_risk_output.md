# Catalyst Narrative Risk Brief

**Primary claim:** Independent measurements indicate the pilot reduced energy use by approximately 12 percent.

**Risk score:** 46 / 100
**Risk level:** Medium
**Coverage:** partial
**Sources / evidence / relationships:** 2 / 2 / 3
**Independent source groups:** 2
**Narrative map:** partial · 3 nodes · 2 links · 1 issues
**Record ID:** urn:uuid:30000000-0000-4000-8000-000000000001
**Case ID:** urn:uuid:30000000-0000-4000-8000-000000000002
**Method:** urn:catalyst:narrative-risk:method:transparent-heuristic @ 2.0.0
**Schema:** https://sustainablecatalyst.com/schemas/narrative-risk/record/2.0.0
**Evidence ledger schema:** https://sustainablecatalyst.com/schemas/narrative-risk/evidence-ledger/2.0.0
**Narrative map schema:** https://sustainablecatalyst.com/schemas/narrative-risk/narrative-map/2.0.0
**Method snapshot SHA-256:** `75e8284752c6e504cbdef4373ef43d0fad639a39c254079c1194a46a37feff59`

## Decision note

Use cautiously with visible uncertainty, source links, and review notes.

## Claims

- **primary · factual:** Independent measurements indicate the pilot reduced energy use by approximately 12 percent. (`urn:catalyst:narrative-risk:claim:sha256:1111111111111111111111111111111111111111111111111111111111111111`)
- **supporting · predictive:** The observed reduction is likely to persist under comparable operating conditions. (`urn:catalyst:narrative-risk:claim:sha256:2222222222222222222222222222222222222222222222222222222222222222`)

## Evidence relationships

- **support · strong:** “Weather-normalized consumption declined 11.8 percent across the pilot sites.” — Pilot meter audit → Independent measurements indicate the pilot reduced energy use by approximately 12 percent.
- **support · strong:** “The interval dataset shows a 12.1 percent reduction relative to the normalized baseline.” — Utility interval dataset → Independent measurements indicate the pilot reduced energy use by approximately 12 percent.
- **qualify · limited:** “Weather-normalized consumption declined 11.8 percent across the pilot sites.” — Pilot meter audit → The observed reduction is likely to persist under comparable operating conditions.

## Narrative map

- **primary · factual_claim · qualified:** Independent measurements indicate the pilot reduced energy use by approximately 12 percent.
- **supporting · predictive_claim · tentative:** The observed reduction is likely to persist under comparable operating conditions.
- **context · assumption · qualified:** Operating schedules, occupancy, and weather remain comparable to the measured pilot period.

### Narrative relationships

- **depends_on · strong:** The observed reduction is likely to persist under comparable operating conditions. → Operating schedules, occupancy, and weather remain comparable to the measured pilot period.
- **supports · limited:** Independent measurements indicate the pilot reduced energy use by approximately 12 percent. → The observed reduction is likely to persist under comparable operating conditions.

### Narrative diagnostics

- **medium · ambiguous_language:** Ambiguous terms require operational definitions: likely. Replace or define vague terms using measurable criteria, scope, and timeframe.

## Flags

- High-consequence claim needs stricter review

## Review actions

- Add at least one independent source or primary reference.
- Escalate to domain, legal, compliance, or editorial review as appropriate.
- Record a reviewer, date, and decision before treating the claim as approved.
- Replace or define vague terms using measurable criteria, scope, and timeframe.

## Component calculations

- **Source Type:** official_or_primary → 0 points
- **Evidence Strength:** strong → 0 points
- **Uncertainty:** medium → 10 points
- **Narrative Volatility:** low → 3 points
- **Stakeholder Pressure:** medium → 10 points
- **Time Sensitivity:** medium → 10 points
- **Consequences:** high → 18 points
- **Review Status:** partly_reviewed → 8 points
- **Source Count:** 2 → 8 points

## Human decision

- Status: draft
- Disposition: undecided

## Source List

- Energy Audit Team (2026) Pilot meter audit. Independent Audit Group. Available at: https://example.org/pilot-audit (Accessed: 2026-07-17).
- City Utility (2026) Utility interval dataset. City Utility. Available at: https://example.org/utility-data (Accessed: 2026-07-17).

The heuristic interpretation is advisory. Approval or rejection must be recorded separately by a human reviewer.
