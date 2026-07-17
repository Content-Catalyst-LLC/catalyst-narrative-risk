# Stakeholder, Incentive, and Pressure Intelligence

Catalyst Narrative Risk v1.7.0 adds an evidence-linked stakeholder layer to persistent cases. It records observable actors and relationships without inferring hidden motives or changing the canonical analytical score automatically.

## Records

- **Actors** identify individuals, communities, organizations, companies, governments, regulators, funders, media, research institutions, advocacy groups, and publics. Each actor may include interests, influence, stance, and disclosure status.
- **Relationships** connect two actors through typed, directed or mutual links such as funding, employment, regulation, representation, advice, partnership, competition, dependence, supply, influence, amplification, contestation, benefit, or harm.
- **Incentives** record financial, political, reputational, legal, social, operational, mission, career, ideological, or other incentives. Potential and confirmed conflicts remain explicit; confirmed conflicts require evidence identifiers.
- **Pressures** record intensity, time horizon, status, source actor, and evidence for financial, political, reputational, legal, social, operational, deadline, funding, media, or public pressure.
- **Consequences** identify stakeholder-specific benefits, harms, mixed outcomes, affected claims, severity, mitigation, and supporting evidence.

## Advisory intelligence

The workspace calculates an inspectable actor-pressure ranking from declared influence, recorded pressure intensity, and disclosed conflict status. It reports flags for high or critical active pressure, potential or confirmed conflicts, high-magnitude undisclosed incentives, and serious harm exposure.

The resulting `suggested_stakeholder_pressure` is advisory. It is not copied into the analytical record automatically. A reviewer must decide whether the canonical scoring input should change and preserve that choice in a new immutable revision.

## Persistence and portability

Stakeholder records are stored in dedicated SQLite tables and are included in portable case bundles with the generated intelligence summary and SHA-256 checksum. Bundle verification checks case identifiers, revision hashes, stakeholder references, and the complete bundle digest before import.

## Interfaces

The REST API, workspace CLI, and WordPress workspace can create and inspect stakeholder records. Institutional systems should use the SQLite-backed API. Browser-local mode is intended for demonstrations and private single-device review.
