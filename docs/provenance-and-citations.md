# Provenance and citations

## Provenance

Source provenance records how a source entered Catalyst Narrative Risk:

- `manual`
- `knowledge_library`
- `catalyst_data`
- `api`
- `document_import`
- `other`

`imported_from` retains the originating system identifier, `imported_at` records the transfer time, and `content_sha256` can bind the source record to an exact imported representation.

Provenance does not establish source quality. It establishes traceability.

## Independence and duplication

`independence_group` represents common production or control. Multiple publications can therefore count as one independent group. `duplicate_of_source_id` records a direct duplicate or derivative copy and automatically inherits the original independence group when the duplicate has no explicit group.

## Directness and freshness

Directness values are `direct`, `indirect`, `mixed`, and `unknown`. Freshness values are `current`, `aging`, `stale`, and `unknown`. The current method adds visible review flags for stale primary-claim sources and for primary claims supported only by indirect or unknown-directness sources.

## Harvard-style source lists

Each normalized source receives a stable citation key and a generated source-list entry. Citations use available creators, year, title, publisher, URL, and access date. Missing metadata is represented transparently with `Unknown author` or `n.d.` rather than fabricated.

Generated citations are a portable baseline. Institutional style guides may reformat them, but source identity and provenance should remain unchanged.
