# Repository Architecture

Catalyst Narrative Risk is organized around a small core engine and public demonstration layer.

```text
narrative_risk/                     Core scoring and record construction
python/                             CLI brief generator
data/                               Sample input records
outputs/                            Example outputs
schemas/                            JSON schema
docs/                               Methodology and review documentation
wordpress/catalyst-narrative-risk-demo/  WordPress shortcode plugin
tests/                              Pytest validation
.github/workflows/                  CI
```

The repository should remain dependency-light and easy to inspect.
