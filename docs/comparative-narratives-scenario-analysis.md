# Comparative Narratives and Scenario Analysis

Catalyst Narrative Risk v1.8.0 adds a persistent comparative layer for examining multiple immutable narrative-risk records without changing any canonical analytical record.

## Comparison sets

A comparison set contains at least two distinct records. Each member identifies its record and optional workspace revision, label, frame, assumptions, tags, and selection state. One member is declared as the baseline for scenario and sensitivity calculations.

Comparison sets support revision, record, scenario, and mixed modes. They do not identify a winning narrative or certify that a member is true.

## Comparative evidence matrices

The evidence matrix aligns claim text across members and reports, for each member:

- linked claim identifiers;
- coverage status;
- support, qualification, contradiction, context, and unresolved counts;
- source and independent-source counts; and
- contradiction counts.

The matrix summary identifies coverage divergence. Divergence is a review signal, not proof that one claim is correct.

## Scenarios

The supported scenario types are best case, base case, worst case, counterfactual, adversarial, and custom. A scenario records explicit assumptions and supported parameter overrides. Scenario evaluation creates a separate checksummed result and leaves the baseline record unchanged.

Supported sensitivity and scenario fields are source type, evidence strength, uncertainty, narrative volatility, stakeholder pressure, time sensitivity, consequences, review status, and source count.

## Sensitivity analysis

Sensitivity analysis runs the declared v1.8.0 method across controlled values for selected dimensions. It reports score ranges and ranks the inputs that create the largest score movement. Results remain dependent on the declared method snapshot and should be interpreted as model sensitivity, not real-world probability.

## Comparative portfolios

A case portfolio aggregates comparison, member, scenario, result, risk-distribution, sensitivity-driver, and governance-readiness information. It is a dashboard artifact derived from persistent records and can always be regenerated.

## Integrity

Comparison matrices, scenario results, sensitivity analyses, portfolios, Decision Studio handoffs, and complete case bundles carry SHA-256 integrity values. Bundle import verifies record hashes, case references, comparative references, and derived-artifact hashes before writing data.

## Boundary

Comparative analysis evaluates explicit records, frames, assumptions, evidence, and scenario parameters. It does not certify truth, infer an optimal narrative, select a preferred scenario automatically, or alter a canonical score.
