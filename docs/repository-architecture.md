# Repository Architecture

The v1.4.0 repository separates six concerns:

- contracts and schemas
- evidence-ledger construction
- claim decomposition and narrative mapping
- analytical scoring and interpretation
- persistent case and review workspaces
- interfaces, integrations, migrations, and release validation

`narrative_risk/narrative_map.py` is independent of `ledger.py`: structural relationships do not become evidence relationships accidentally. `service.py` composes both into the canonical six-layer record. `workspaces.py` stores those records as immutable revisions while keeping mutable case metadata and append-only review activity separate.
