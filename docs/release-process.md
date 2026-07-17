# Release process

Install the declared development dependencies and run:

```bash
bash scripts/release_check.sh
```

The release suite validates Python tests, Python syntax, required files, version consistency, JSON syntax, JSON Schema output, JavaScript syntax, browser fixtures, direct cross-runtime parity, CLI export, and WordPress PHP syntax.

A release must not be packaged if any check fails.
