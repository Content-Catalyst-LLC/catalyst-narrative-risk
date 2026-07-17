# Review, Approval, and Governance Workflow

Catalyst Narrative Risk v1.5.0 adds a governed review layer around immutable analytical revisions. The analytical record remains advisory and reproducible. A score, flag, or narrative-map diagnostic never creates an approval automatically.

## Governance boundary

A case may have one active governance workflow tied to one immutable revision. The workflow stores a complete review-template snapshot so later policy changes do not rewrite the historical review path.

The canonical stage order is:

1. Intake
2. Domain
3. Editorial
4. Legal
5. Compliance
6. Final

Templates may mark legal and compliance stages optional, but the final stage is always required. Stage order cannot be rearranged.

## Review assignments

Assignments record:

- case, revision, workflow, and stage identifiers;
- reviewer identity and governance role;
- required or optional status;
- instructions and due date;
- pending, accepted, completed, waived, or overdue state;
- acceptance, completion, and escalation timestamps.

Due-state calculation is transparent. A pending or accepted assignment is reported as overdue when its due date has passed. The stored assignment remains append-only except for explicit status transitions.

## Governance decisions

Every stage decision is an append-only record with:

- an explicit disposition;
- an authorized decision maker and role;
- rationale;
- conditions;
- required wording;
- publication restrictions;
- disclosures;
- validity and reassessment dates;
- an optional superseded-decision reference.

Supported dispositions are `approve`, `approve_with_conditions`, `revise`, `reject`, and `waive`.

A conditional approval must carry at least one condition, wording requirement, restriction, or disclosure. Final approval requires all required assignments to be completed or waived and no unresolved revise or reject decision.

## Publication controls

Publication is allowed only when the workflow is approved, its approval has not expired, reassessment is not due, and the final decision does not contain a blocking restriction.

Blocking restrictions are:

- `internal_only`
- `embargoed`
- `no_public_claim`
- `legal_review_required`

`attribution_required` and `disclosure_required` permit publication when their obligations are satisfied operationally.

## Expiration and reassessment

`valid_until` causes an approved workflow to be reported as expired after that date. `reassessment_at` creates a reassessment-due flag even when the approval itself is still valid. These are derived governance states; they do not alter the historical decision record.

## Role permissions

The versioned method snapshot defines permissions for authors, reviewers, domain reviewers, editorial reviewers, legal reviewers, compliance reviewers, final approvers, administrators, and observers.

Only authorized roles may assign reviewers, decide a stage, approve the final stage, manage templates, override expiration, or publish. The permission policy travels with the analytical method snapshot so a record can be interpreted against the policy in force when it was created.

## Portable governance bundles

The v1.5.0 case bundle includes:

- case metadata;
- immutable revisions;
- review events;
- append-only activity;
- the governance workflow;
- review assignments;
- governance decisions;
- one bundle SHA-256 checksum.

Import verifies the bundle checksum, all revision hashes, and all case identifiers before writing any data. Import is transactional, and an export-import-re-export round trip is exact.
