# Catalyst Canvas Stakeholder Handoff

The v1.7.0 Catalyst Canvas handoff imports explicitly selected stakeholder and relationship records into an existing Narrative Risk case.

## Contract

The handoff must identify its source as Catalyst Canvas, carry a versioned handoff identifier, target one Narrative Risk case, and provide explicit actors and relationships. Canvas identifiers are retained in `external_id` and handoff provenance records.

All actor and relationship references are validated before any database writes occur. A malformed relationship therefore cannot leave a partially imported actor set.

## Boundary

The handoff imports declared Canvas structure. It does not convert a persona, stakeholder map, or journey assumption into verified evidence. Reviewers must attach evidence independently and may revise influence, stance, disclosure, and relationship strength after import.

## Example

See `data/handoffs/catalyst_canvas_stakeholder_handoff.json`.
