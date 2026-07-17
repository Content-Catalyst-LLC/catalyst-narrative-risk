# Claims, sources, and evidence ledger

## Purpose

The v1.5.0 ledger makes each material narrative-risk conclusion traceable. It records review objects and relationships rather than treating a source count as evidence by itself.

## Claims

A ledger contains exactly one `primary` claim and may contain `supporting` or `context` claims. Claim types are `factual`, `causal`, `predictive`, `normative`, `recommendation`, and `interpretive`.

The top-level `claim` must exactly match the text of the primary claim. When no claims array is supplied, the engine creates a deterministic primary factual claim from that text.

## Sources

A source record can carry:

- Title, creators, publisher, publication year, URL, and access timestamp
- DOI, ISBN, ISSN, URL, handle, ARK, catalog, or other identifiers
- Source class used by the method
- Independence group and optional duplicate-of relationship
- Directness and freshness classifications
- Acquisition method, originating object, import timestamp, and content SHA-256
- Reviewer notes

A duplicate source is still retained as a source record, but it follows the original source's independence group when no explicit group is supplied.

## Evidence items

Evidence items belong to one source and contain an excerpt, evidence type, locator, capture timestamp, notes, and generated `excerpt_sha256`. The hash detects changed excerpt content without replacing source review.

## Relationships

Each relationship connects one claim to one evidence item and records:

- `support`
- `qualify`
- `contradict`
- `contextualize`
- `unresolved`

Relationship strength uses `strong`, `moderate`, `limited`, `weak`, or `unclear`.

## Coverage

Per-claim coverage reports unique evidence, sources, independent source groups, relationship counts, strongest positive relationship, contestation, and one of:

- `none`
- `partial`
- `substantial`
- `contested`

Overall coverage aggregates counts but does not declare truth. A claim may have substantial coverage and still be incorrect, mis-scoped, or unsuitable for a particular use.

## Derived scoring inputs

When the primary claim has relationships, the ledger is authoritative for source-related scoring inputs. The method counts unique linked sources, selects the lowest-risk linked positive source type, and derives evidence strength using the embedded independence and contradiction policy.
