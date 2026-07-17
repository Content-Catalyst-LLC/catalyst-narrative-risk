# Release process

Run the canonical gate from the repository root:

```bash
python -m pip install -r requirements-dev.txt
bash scripts/release_check.sh
```

The gate performs:

- Python tests and compile checks
- Required-file, version, identifier, schema, method, migration, fixture, output, and WordPress contracts
- Generated browser-method drift detection
- JavaScript syntax and browser-engine fixture tests
- Direct Python–JavaScript analysis and full-record parity
- CLI JSON, Markdown, bibliography, and evidence-ledger CSV generation
- Exact record verification
- v1.0.1 and v1.1.0 migration and post-migration verification
- PHP syntax validation

A release package must exclude virtual environments, caches, generated temporary state, and secrets. Published ZIP files receive SHA-256 checksums and are independently unpacked and retested before delivery.
