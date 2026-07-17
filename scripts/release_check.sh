#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
PHP="${PHP:-php}"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cnrisk-v170.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
export CNRISK_DATABASE_PATH="$TMP_DIR/api-tests.sqlite3"

printf '\n==> Python tests (isolated workspace database)\n'
"$PYTHON" -m pytest -q

printf '\n==> Python compile and canonical release contract\n'
"$PYTHON" -m compileall -q app narrative_risk python scripts tests
"$PYTHON" scripts/release_contract.py
"$PYTHON" scripts/generate_browser_method_asset.py --check

printf '\n==> Browser syntax, fixture matrix, map parity, record parity, and workspace syntax\n'
for file in \
  wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-method.js \
  wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-map.js \
  wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js \
  wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-demo.js \
  wordpress/catalyst-narrative-risk-demo/assets/catalyst-narrative-risk-workspace.js \
  scripts/browser_record_dump.js scripts/browser_fixture_dump.js; do
  "$NODE" --check "$file"
done
"$NODE" scripts/test_browser_engine.js
"$PYTHON" scripts/cross_runtime_parity.py
"$PYTHON" scripts/cross_runtime_record_parity.py

printf '\n==> CLI brief, ledger exports, map exports, and exact reproduction\n'
"$PYTHON" python/narrative_risk_brief.py \
  --input data/sample_narrative_risk_input.json \
  --json-out "$TMP_DIR/sample.json" --markdown-out "$TMP_DIR/sample.md" \
  --bibliography-out "$TMP_DIR/source-list.md" \
  --generated-at 2026-07-17T12:00:00+00:00 \
  --record-id urn:uuid:30000000-0000-4000-8000-000000000001 \
  --case-id urn:uuid:30000000-0000-4000-8000-000000000002
"$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/sample.json"
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.json" --format json
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.md" --format markdown
"$PYTHON" python/export_evidence_ledger.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/ledger.csv" --format csv
"$PYTHON" python/export_narrative_map.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/map.json" --format json
"$PYTHON" python/export_narrative_map.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/map.md" --format markdown
"$PYTHON" python/export_narrative_map.py --input "$TMP_DIR/sample.json" --output "$TMP_DIR/map.mmd" --format mermaid
for output in sample.md source-list.md ledger.json ledger.md ledger.csv map.json map.md map.mmd; do test -s "$TMP_DIR/$output"; done
grep -q 'relationship_id,claim_id,claim_text' "$TMP_DIR/ledger.csv"
grep -q 'flowchart TD' "$TMP_DIR/map.mmd"
grep -q 'Narrative Map' "$TMP_DIR/map.md"

printf '\n==> Persistent workspace, governance, monitoring, stakeholder CLI, and portable bundle round trip\n'
SOURCE_DB="$TMP_DIR/source.sqlite3"; TARGET_DB="$TMP_DIR/target.sqlite3"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" init > "$TMP_DIR/workspace-health.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" create \
  --title "Release narrative-map case" --summary "Persistent v1.7.0 release verification." \
  --status in_review --priority high --tag release --tag narrative-map \
  --input data/sample_narrative_risk_input.json --created-by release-suite > "$TMP_DIR/case.json"
CASE_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["case_id"])' "$TMP_DIR/case.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" show "$CASE_ID" --details > "$TMP_DIR/case-details.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" add-review "$CASE_ID" \
  --event-type comment --author-id release-suite --body "Narrative-map release review event." > "$TMP_DIR/review.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" create-template \
  --name "Release governance template" --created-by release-suite --actor-role administrator > "$TMP_DIR/template.json"
TEMPLATE_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["template_id"])' "$TMP_DIR/template.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" list-templates --active true > "$TMP_DIR/templates.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" start-governance "$CASE_ID" \
  --template-id "$TEMPLATE_ID" --started-at 2026-07-17T13:00:00+00:00 \
  --due-at 2026-07-31T13:00:00+00:00 --created-by release-suite --actor-role administrator > "$TMP_DIR/workflow.json"
WORKFLOW_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["workflow_id"])' "$TMP_DIR/workflow.json")"
for spec in \
  "intake|intake-reviewer|reviewer" \
  "domain|domain-reviewer|domain_reviewer" \
  "editorial|editorial-reviewer|editorial_reviewer" \
  "final|final-approver|final_approver"; do
  IFS='|' read -r STAGE REVIEWER ROLE <<< "$spec"
  "$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" assign-review "$WORKFLOW_ID" \
    --stage "$STAGE" --reviewer-id "$REVIEWER" --reviewer-role "$ROLE" \
    --due-at 2026-07-24T17:00:00+00:00 --created-by release-suite --actor-role administrator > "$TMP_DIR/assignment-$STAGE.json"
done
for spec in \
  "intake|intake-reviewer|reviewer" \
  "domain|domain-reviewer|domain_reviewer" \
  "editorial|editorial-reviewer|editorial_reviewer"; do
  IFS='|' read -r STAGE REVIEWER ROLE <<< "$spec"
  ASSIGNMENT_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["assignment_id"])' "$TMP_DIR/assignment-$STAGE.json")"
  "$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" decide "$WORKFLOW_ID" \
    --stage "$STAGE" --disposition approve --assignment-id "$ASSIGNMENT_ID" \
    --decided-by "$REVIEWER" --decider-role "$ROLE" --rationale "$STAGE release review passed." > "$TMP_DIR/decision-$STAGE.json"
done
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" decide "$WORKFLOW_ID" \
  --stage legal --disposition waive --decided-by release-suite --decider-role administrator \
  --rationale "Separate legal review is not required for this release fixture." > "$TMP_DIR/decision-legal.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" decide "$WORKFLOW_ID" \
  --stage compliance --disposition waive --decided-by release-suite --decider-role administrator \
  --rationale "Separate compliance review is not required for this release fixture." > "$TMP_DIR/decision-compliance.json"
FINAL_ASSIGNMENT_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["assignment_id"])' "$TMP_DIR/assignment-final.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" decide "$WORKFLOW_ID" \
  --stage final --disposition approve_with_conditions --assignment-id "$FINAL_ASSIGNMENT_ID" \
  --decided-by final-approver --decider-role final_approver \
  --rationale "Release governance checks passed with explicit publication controls." \
  --condition "Preserve method limitations." --required-wording "Describe the score as advisory." \
  --publication-restriction attribution_required --disclosure "Disclose heuristic review status." \
  --valid-until 2027-01-17T15:00:00+00:00 --reassessment-at 2026-10-17T15:00:00+00:00 > "$TMP_DIR/decision-final.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" governance-queue --reviewer-id final-approver > "$TMP_DIR/governance-queue.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" reassessment-due --at 2026-10-18T15:00:00+00:00 > "$TMP_DIR/reassessment-due.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" capture-snapshot "$CASE_ID" \
  --captured-at 2026-07-18T12:00:00+00:00 --trigger manual > "$TMP_DIR/snapshot.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" create-watch "$CASE_ID" \
  --name "Release monitoring watch" --cadence daily --trigger-type source_stale \
  --trigger-type material_change --trigger-type reassessment_due --trigger-type approval_expired \
  --created-by release-suite > "$TMP_DIR/watch.json"
WATCH_ID="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["watch_id"])' "$TMP_DIR/watch.json")"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" check-watch "$WATCH_ID" \
  --checked-at 2028-07-18T12:00:00+00:00 > "$TMP_DIR/watch-check.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" list-watches --case-id "$CASE_ID" > "$TMP_DIR/watches.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" list-alerts --case-id "$CASE_ID" > "$TMP_DIR/alerts.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" timeline "$CASE_ID" > "$TMP_DIR/timeline.json"
"$PYTHON" - "$CASE_ID" data/handoffs/site_intelligence_monitoring_event.json "$TMP_DIR/site-event.json" <<'PY'
import json,sys
case_id,source,target=sys.argv[1:]
payload=json.load(open(source)); payload["case_id"]=case_id
json.dump(payload,open(target,"w"),indent=2); open(target,"a").write("\n")
PY
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" ingest-site-intelligence \
  --input "$TMP_DIR/site-event.json" --ingested-at 2026-07-20T12:01:00+00:00 > "$TMP_DIR/site-intelligence.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" import-catalyst-canvas "$CASE_ID" \
  --input data/handoffs/catalyst_canvas_stakeholder_handoff.json --imported-at 2026-07-17T19:00:00+00:00 > "$TMP_DIR/canvas-import.json"
"$PYTHON" - "$TMP_DIR/canvas-import.json" "$TMP_DIR/incentive.json" "$TMP_DIR/pressure.json" "$TMP_DIR/consequence.json" <<'PYDATA'
import json,sys
source,incentive_path,pressure_path,consequence_path=sys.argv[1:]
data=json.load(open(source)); actors=data["actors"]
funder=next(item for item in actors if item.get("external_id","").endswith(":funder"))
evaluator=next(item for item in actors if item.get("external_id","").endswith(":evaluator"))
community=next(item for item in actors if item.get("external_id","").endswith(":community"))
json.dump({"actor_id":funder["actor_id"],"incentive_type":"reputational","description":"Demonstrate measurable public impact.","magnitude":"high","alignment":"mixed","disclosed":True,"conflict_status":"potential"},open(incentive_path,"w"),indent=2)
json.dump({"actor_id":evaluator["actor_id"],"source_actor_id":funder["actor_id"],"pressure_type":"deadline","description":"Publish before board review.","intensity":"critical","time_horizon":"immediate","status":"active"},open(pressure_path,"w"),indent=2)
json.dump({"actor_id":community["actor_id"],"impact_type":"financial","direction":"mixed","severity":"high","description":"Overstatement could distort affordability expectations.","mitigation":"Publish confidence limits and measurement dates."},open(consequence_path,"w"),indent=2)
PYDATA
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" add-stakeholder-incentive "$CASE_ID" --input "$TMP_DIR/incentive.json" > "$TMP_DIR/incentive-output.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" add-stakeholder-pressure "$CASE_ID" --input "$TMP_DIR/pressure.json" > "$TMP_DIR/pressure-output.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" add-stakeholder-consequence "$CASE_ID" --input "$TMP_DIR/consequence.json" > "$TMP_DIR/consequence-output.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" stakeholder-intelligence "$CASE_ID" --generated-at 2026-07-17T20:00:00+00:00 > "$TMP_DIR/stakeholder-intelligence.json"
"$PYTHON" - "$TMP_DIR/stakeholder-intelligence.json" <<'PYDATA'
import json,sys
value=json.load(open(sys.argv[1]))
assert value["counts"] == {"actors":3,"relationships":2,"incentives":1,"pressures":1,"consequences":1}
assert value["suggested_stakeholder_pressure"] == "high"
assert value["intelligence_sha256"]
PYDATA
"$PYTHON" python/narrative_risk_workspace.py --database "$SOURCE_DB" export "$CASE_ID" \
  --output "$TMP_DIR/case-bundle.json" --exported-at 2026-07-17T17:00:00+00:00
"$PYTHON" python/narrative_risk_workspace.py verify-bundle --input "$TMP_DIR/case-bundle.json" > "$TMP_DIR/bundle-verification.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" import --input "$TMP_DIR/case-bundle.json" > "$TMP_DIR/imported.json"
"$PYTHON" python/narrative_risk_workspace.py --database "$TARGET_DB" export "$CASE_ID" \
  --output "$TMP_DIR/reexported.json" --exported-at 2026-07-17T17:00:00+00:00
cmp "$TMP_DIR/case-bundle.json" "$TMP_DIR/reexported.json"

printf '\n==> Legacy migrations and post-migration reproduction\n'
for legacy in 1.0.1 1.1.0 1.2.0 1.3.0 1.4.0 1.5.0 1.6.0; do
  "$PYTHON" python/migrate_narrative_risk_record.py \
    --input "tests/fixtures/legacy-v${legacy}-record.json" \
    --output "$TMP_DIR/migrated-${legacy}.json" --migrated-at 2026-07-17T18:00:00+00:00
  "$PYTHON" python/verify_narrative_risk_record.py --input "$TMP_DIR/migrated-${legacy}.json"
done

printf '\n==> WordPress PHP syntax\n'
"$PHP" -l wordpress/catalyst-narrative-risk-demo/catalyst-narrative-risk-demo.php

printf '\nCatalyst Narrative Risk v1.7.0 release suite passed.\n'
