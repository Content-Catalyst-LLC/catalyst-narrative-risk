# Reproducibility

A v1.6.0 record can be rebuilt exactly from its normalized input, evidence ledger inputs, narrative-map inputs, method snapshot, identifiers, generation timestamp, human decision, and optional migration metadata.

Verification checks:

- method snapshot SHA-256
- normalized-input SHA-256
- evidence-ledger SHA-256
- narrative-map SHA-256
- full record-payload SHA-256
- exact canonical record equality

```bash
python python/verify_narrative_risk_record.py --input record.json
```

Python and browser runtimes use identical canonical JSON ordering and SHA-256 rules. The browser method asset is generated from the versioned method JSON; the map engine is tested against the same valid and invalid fixtures as Python.
