# Scoped REST API and OpenAPI

The Flask service exposes an OpenAPI 3.1 discovery document at:

```text
/api/narrative-risk/openapi.json
```

## Authentication

Set `NARRATIVE_RISK_REQUIRE_API_KEY=true` in the application configuration to require bearer credentials for publication endpoints. API secrets are returned only once when created; only their SHA-256 digest and short prefix are stored.

```http
Authorization: Bearer cnr_...
```

Supported scopes are:

- `records:read`
- `cases:read`
- `cases:write`
- `publication:read`
- `publication:write`
- `embeds:read`
- `embeds:write`
- `handoffs:write`
- `admin`

An `admin` key satisfies any scope. Keys may expire, be revoked, and have a rate limit from 1 to 1,000 requests per minute.

## Core publication routes

```text
POST /api/narrative-risk/cases/{case_id}/briefings
GET  /api/narrative-risk/cases/{case_id}/briefings
POST /api/narrative-risk/briefings/{briefing_id}/packages
GET  /api/narrative-risk/cases/{case_id}/publications
PATCH /api/narrative-risk/packages/{package_id}
GET  /api/narrative-risk/packages/{package_id}/artifacts/{format}
POST /api/narrative-risk/packages/{package_id}/embeds
GET  /api/narrative-risk/cases/{case_id}/embeds
GET  /api/narrative-risk/embed/{slug}
POST /api/narrative-risk/packages/{package_id}/handoffs
GET  /api/narrative-risk/cases/{case_id}/publication-handoffs
```

API-key creation can be protected with `NARRATIVE_RISK_ADMIN_TOKEN`, supplied as `X-CNRISK-Admin-Token`. Key listing and revocation require the `admin` scope when API-key enforcement is enabled.

The API does not bypass governance. A request for a public briefing fails when the referenced case lacks a current publication approval.
