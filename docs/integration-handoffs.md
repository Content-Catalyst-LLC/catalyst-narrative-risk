# Integration handoffs

v1.6.0 provides narrow source-import contracts rather than coupling Narrative Risk to another product's database.

## Knowledge Library

`schemas/knowledge_library_source_handoff.schema.json` accepts a document identity, title, optional authors and publication metadata, canonical URL, access time, content hash, source class, and notes.

The adapter creates a Narrative Risk source with:

- A deterministic source ID based on the Knowledge Library document ID
- A `knowledge-library:<document_id>` catalog identifier and independence group
- `knowledge_library` acquisition provenance
- The original document identity and content hash

## Catalyst Data

`schemas/catalyst_data_source_handoff.schema.json` accepts a dataset identity, title, creators, publisher, publication year, landing page, access time, content hash, source class, and notes.

The adapter creates a direct source with:

- A deterministic source ID based on the Catalyst Data dataset ID
- A `catalyst-data:<dataset_id>` catalog identifier and independence group
- `catalyst_data` acquisition provenance
- The original dataset identity and content hash

## API endpoints

- `POST /api/narrative-risk/import/knowledge-library`
- `POST /api/narrative-risk/import/catalyst-data`

The response is a normalized source input that can be inserted into a record's `sources` array. The handoffs do not automatically create claims, excerpts, or relationships; reviewers must explicitly connect imported sources to evidence and claims.
