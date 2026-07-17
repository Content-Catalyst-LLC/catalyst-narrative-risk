# Decision Studio Comparative Handoff

Catalyst Narrative Risk v1.8.0 can export a checksummed comparative packet for Sustainable Catalyst Decision Studio.

The handoff includes:

- the complete comparison set and baseline designation;
- the latest comparative evidence matrix;
- selected scenario identifiers and their evaluated results;
- the latest sensitivity analysis;
- the case-level comparative portfolio;
- governance status, final disposition, publication restrictions, and readiness context; and
- an explicit advisory boundary.

Decision Studio may use this packet to construct decision options, scenario briefs, trade-off views, or decision packets. It must preserve source identifiers, record identifiers, scenario assumptions, method versions, and integrity hashes.

The handoff does not direct Decision Studio to choose a narrative. Selection and approval remain explicit human decisions governed by the receiving workflow.

## CLI

```bash
python python/narrative_risk_workspace.py --database instance/catalyst-narrative-risk.sqlite3 \
  decision-studio-handoff COMPARISON_ID --scenario-id SCENARIO_ID
```

## REST

```text
POST /api/narrative-risk/comparisons/{comparison_id}/decision-studio-handoff
```

The optional request body can contain `selected_scenario_ids` and `generated_at`.
