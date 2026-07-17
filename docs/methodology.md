# Methodology

Catalyst Narrative Risk uses a transparent additive heuristic. Each normalized input maps to an inspectable component weight. The component total is multiplied by `0.68`, rounded to the nearest integer, and clamped to 0–100.

Risk levels are:

- Low: 0–39
- Medium: 40–69
- High: 70–100

Valid zero-weight values are intentional and must remain zero:

- `official_or_primary` source type;
- `strong` evidence strength;
- `reviewed` review status.

The source-count penalty declines as independent support increases. Flags and actions are deterministic consequences of normalized inputs, not generated opinions.

Unsupported choice values fall back to documented defaults. Missing claims, malformed source counts, unsupported fields, and non-object payloads are rejected.

This method structures review. It does not verify truth, infer intent, certify evidence, approve communications, or replace domain, legal, scientific, compliance, or editorial judgment.
