# WordPress Publication Interfaces

Catalyst Narrative Risk v1.9.0 includes four shortcodes:

```text
[catalyst_narrative_risk_demo]
[catalyst_narrative_risk_workspace]
[catalyst_narrative_risk_publication_workspace]
[catalyst_narrative_risk_public_brief]
```

## Publication workspace

`[catalyst_narrative_risk_publication_workspace]` provides a browser preview for an already governed briefing and can export preview JSON, Markdown, and HTML. It does not create institutional approval. Production PDF, CSV, JSON-LD, embed, API, and platform-handoff records must be created through the persistent v1.9.0 REST workspace.

## Public brief

The public-display shortcode accepts escaped presentation attributes:

```text
[catalyst_narrative_risk_public_brief
  title="Reviewed Narrative Brief"
  claim="Available evidence indicates the initiative may improve public trust."
  score="18"
  level="moderate"
  evidence="Two independent sources; no unresolved contradiction."
  governance="Approved with attribution and disclosure conditions."
  disclosure="Evidence reviewed July 17, 2026."
  reassessment="December 15, 2026"]
```

For institutional use, populate the page from a published package or public embed rather than manually duplicating review data.
