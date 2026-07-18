<?php
/**
 * Plugin Name: Catalyst Narrative Risk
 * Description: Narrative-risk scoring, evidence, mapping, governance, monitoring, comparative analysis, publication briefings, public embeds, and persistent review workspaces for Sustainable Catalyst.
 * Version: 1.10.0
 * Author: Content Catalyst LLC
 * License: MIT
 */

if (!defined('ABSPATH')) {
    exit;
}

function cnrisk_demo_assets() {
    $base = plugin_dir_url(__FILE__);
    wp_register_style('cnrisk-demo-css', $base . 'assets/catalyst-narrative-risk-demo.css', array(), '1.10.0');
    wp_register_script('cnrisk-method-js', $base . 'assets/narrative-risk-method.js', array(), '1.10.0', true);
    wp_register_script('cnrisk-map-js', $base . 'assets/narrative-risk-map.js', array(), '1.10.0', true);
    wp_register_script('cnrisk-engine-js', $base . 'assets/narrative-risk-engine.js', array('cnrisk-method-js', 'cnrisk-map-js'), '1.10.0', true);
    wp_register_script('cnrisk-demo-js', $base . 'assets/catalyst-narrative-risk-demo.js', array('cnrisk-engine-js'), '1.10.0', true);
    wp_register_style('cnrisk-workspace-css', $base . 'assets/catalyst-narrative-risk-workspace.css', array(), '1.10.0');
    wp_register_script('cnrisk-workspace-js', $base . 'assets/catalyst-narrative-risk-workspace.js', array('cnrisk-engine-js'), '1.10.0', true);
    wp_register_style('cnrisk-publication-css', $base . 'assets/catalyst-narrative-risk-publication.css', array(), '1.10.0');
    wp_register_script('cnrisk-publication-js', $base . 'assets/catalyst-narrative-risk-publication.js', array(), '1.10.0', true);
}
add_action('wp_enqueue_scripts', 'cnrisk_demo_assets');

function cnrisk_demo_shortcode() {
    wp_enqueue_style('cnrisk-demo-css');
    wp_enqueue_script('cnrisk-demo-js');

    ob_start();
    ?>
    <div class="cnrisk-demo" data-cnrisk-demo>
      <div class="cnrisk-demo__head">
        <p class="cnrisk-demo__eyebrow">Interactive demo</p>
        <h3>Catalyst Narrative Risk</h3>
        <p>Build a traceable review record linking claims to sources, evidence excerpts, narrative structure, assumptions, wording variants, uncertainty, and human judgment.</p>
      </div>

      <div class="cnrisk-demo__grid">
        <form class="cnrisk-demo__form" data-cnrisk-form>
          <label>
            <span>Claim or narrative statement</span>
            <textarea name="claim" rows="4">The proposed sustainability initiative will materially improve public trust within one year.</textarea>
          </label>

          <div class="cnrisk-demo__two">
            <label>
              <span>Source type</span>
              <select name="source_type">
                <option value="official_or_primary">Official / primary</option>
                <option value="peer_reviewed_or_audited">Peer reviewed / audited</option>
                <option value="reputable_secondary" selected>Reputable secondary</option>
                <option value="internal_unreviewed">Internal, unreviewed</option>
                <option value="single_report_or_media">Single report / media</option>
                <option value="social_or_anecdotal">Social / anecdotal</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>

            <label>
              <span>Evidence strength</span>
              <select name="evidence_strength">
                <option value="strong">Strong</option>
                <option value="moderate">Moderate</option>
                <option value="limited" selected>Limited</option>
                <option value="weak">Weak</option>
                <option value="unclear">Unclear</option>
              </select>
            </label>
          </div>

          <div class="cnrisk-demo__three">
            <label>
              <span>Source count</span>
              <input type="number" name="source_count" min="0" max="20" value="2" />
            </label>
            <label>
              <span>Uncertainty</span>
              <select name="uncertainty">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high" selected>High</option>
              </select>
            </label>
            <label>
              <span>Review status</span>
              <select name="review_status">
                <option value="reviewed">Reviewed</option>
                <option value="partly_reviewed" selected>Partly reviewed</option>
                <option value="not_reviewed">Not reviewed</option>
              </select>
            </label>
          </div>

          <div class="cnrisk-demo__two">
            <label>
              <span>Narrative volatility</span>
              <select name="narrative_volatility">
                <option value="low">Low</option>
                <option value="medium" selected>Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label>
              <span>Stakeholder pressure</span>
              <select name="stakeholder_pressure">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high" selected>High</option>
              </select>
            </label>
          </div>

          <div class="cnrisk-demo__two">
            <label>
              <span>Time sensitivity</span>
              <select name="time_sensitivity">
                <option value="low">Low</option>
                <option value="medium" selected>Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label>
              <span>Consequences if overstated</span>
              <select name="consequences">
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high" selected>High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
          </div>

          <label>
            <span>Method notes</span>
            <textarea name="method_notes" rows="3">Claim needs narrower language, stronger baseline evidence, and a review date before publication.</textarea>
          </label>

          <label>
            <span>Evidence ledger JSON (optional)</span>
            <textarea name="evidence_ledger_json" rows="8" placeholder='{"claims": [...], "sources": [...], "evidence_items": [...], "relationships": [...]}'></textarea>
            <small>When provided, source type, evidence strength, and source count are derived from linked evidence. Use “Load traceable sample” to see the contract.</small>
          </label>

          <label>
            <span>Narrative map JSON (optional)</span>
            <textarea name="narrative_map_json" rows="8" placeholder='{"narrative_nodes": [...], "narrative_links": [...], "wording_variants": [...], "selected_variant_id": "..."}'></textarea>
            <small>Use this contract to decompose compound claims, connect assumptions and causal or predictive dependencies, and compare alternate wording.</small>
          </label>

          <div class="cnrisk-demo__actions">
            <button type="submit">Generate record</button>
            <button type="button" data-cnrisk-sample>Load traceable sample</button>
            <button type="button" data-cnrisk-download>Download JSON</button>
          </div>
        </form>

        <aside class="cnrisk-demo__result" aria-live="polite">
          <p class="cnrisk-demo__error" data-cnrisk-error role="alert" hidden></p>
          <div class="cnrisk-demo__scorebox">
            <span class="cnrisk-demo__label">Narrative risk score</span>
            <strong data-cnrisk-score>—</strong>
            <em data-cnrisk-level>Generate a record</em>
            <div class="cnrisk-demo__meter"><span data-cnrisk-meter></span></div>
          </div>

          <div class="cnrisk-demo__bars" data-cnrisk-bars></div>

          <div class="cnrisk-demo__block">
            <h4>Contract identity</h4>
            <p data-cnrisk-identity>No record generated yet.</p>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Evidence coverage</h4>
            <p data-cnrisk-coverage>No ledger analyzed yet.</p>
            <p><strong>Derived scoring inputs:</strong> <span data-cnrisk-derived>Not yet calculated.</span></p>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Source list</h4>
            <ul data-cnrisk-sources><li>No item-level sources recorded.</li></ul>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Narrative map</h4>
            <p data-cnrisk-map-summary>No narrative map analyzed yet.</p>
            <ul data-cnrisk-map-issues><li>No narrative-map diagnostics generated.</li></ul>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Decision note</h4>
            <p data-cnrisk-note>Complete the form to generate an interpretation note.</p>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Human decision</h4>
            <p data-cnrisk-human>Draft · undecided</p>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Flags</h4>
            <ul data-cnrisk-flags><li>No record generated yet.</li></ul>
          </div>

          <div class="cnrisk-demo__block">
            <h4>Review actions</h4>
            <ul data-cnrisk-actions><li>No record generated yet.</li></ul>
          </div>
        </aside>
      </div>

      <details class="cnrisk-demo__json">
        <summary>View JSON export</summary>
        <pre data-cnrisk-json>{}</pre>
      </details>

      <p class="cnrisk-demo__fineprint">
        This demo is educational and exploratory. It structures review; it does not verify truth, provide legal advice,
        approve communications, or replace professional judgment.
      </p>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('catalyst_narrative_risk_demo', 'cnrisk_demo_shortcode');


function cnrisk_workspace_shortcode() {
    wp_enqueue_style('cnrisk-workspace-css');
    wp_enqueue_script('cnrisk-workspace-js');
    ob_start();
    ?>
    <div class="cnrisk-workspace" data-cnrisk-workspace>
      <header class="cnrisk-workspace__head">
        <h3>Narrative Risk Review Workspace</h3>
        <p>Create durable cases, add immutable revisions, govern approvals, monitor narrative change, map stakeholders and pressures, compare narratives, evaluate scenarios, and export checksummed case bundles.</p>
      </header>
      <div class="cnrisk-workspace__layout">
        <aside class="cnrisk-workspace__sidebar">
          <label><span>Search cases</span><input type="search" data-cnrisk-workspace-search placeholder="Title, summary, or tag" /></label>
          <div class="cnrisk-workspace__actions">
            <button type="button" data-cnrisk-new-case>New case</button>
            <label class="cnrisk-workspace__file">Import bundle<input type="file" accept="application/json" data-cnrisk-import-bundle /></label>
          </div>
          <div data-cnrisk-workspace-list></div>
        </aside>
        <main class="cnrisk-workspace__main">
          <form data-cnrisk-workspace-form>
            <div class="cnrisk-workspace__two">
              <label><span>Case title</span><input name="case_title" required value="New narrative review case" /></label>
              <label><span>Tags</span><input name="case_tags" placeholder="public, energy, pilot" /></label>
            </div>
            <label><span>Case summary</span><textarea name="case_summary" rows="2"></textarea></label>
            <div class="cnrisk-workspace__two">
              <label><span>Status</span><select name="case_status"><option value="draft">Draft</option><option value="active">Active</option><option value="in_review">In review</option><option value="approved">Approved</option><option value="closed">Closed</option></select></label>
              <label><span>Priority</span><select name="case_priority"><option value="low">Low</option><option value="normal" selected>Normal</option><option value="high">High</option><option value="critical">Critical</option></select></label>
            </div>
            <label><span>Claim or narrative statement</span><textarea name="claim" rows="4" required>The proposed initiative will improve public trust.</textarea></label>
            <div class="cnrisk-workspace__two">
              <label><span>Uncertainty</span><select name="uncertainty"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></label>
              <label><span>Review status</span><select name="review_status"><option value="reviewed">Reviewed</option><option value="partly_reviewed" selected>Partly reviewed</option><option value="not_reviewed">Not reviewed</option></select></label>
              <label><span>Narrative volatility</span><select name="narrative_volatility"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></label>
              <label><span>Stakeholder pressure</span><select name="stakeholder_pressure"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></label>
              <label><span>Time sensitivity</span><select name="time_sensitivity"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></label>
              <label><span>Consequences</span><select name="consequences"><option value="low">Low</option><option value="moderate" selected>Moderate</option><option value="high">High</option><option value="critical">Critical</option></select></label>
            </div>
            <label><span>Method notes</span><textarea name="method_notes" rows="2"></textarea></label>
            <label><span>Revision note</span><input name="change_note" placeholder="What changed in this revision?" /></label>
            <div class="cnrisk-workspace__actions">
              <button type="submit">Save revision</button>
              <button type="button" data-cnrisk-archive-case>Archive open case</button>
            </div>
          </form>
          <div class="cnrisk-workspace__notice">
            Browser mode stores cases locally on this device. Institutional deployments should connect the interface to the v1.10.0 SQLite-backed REST workspace API.
          </div>
          <p class="cnrisk-workspace__message" data-cnrisk-workspace-message aria-live="polite"></p>
          <div class="cnrisk-workspace__detail" data-cnrisk-workspace-detail><p>Start a new case or open an existing one.</p></div>
          <section class="cnrisk-workspace__governance" aria-labelledby="cnrisk-governance-heading">
            <h4 id="cnrisk-governance-heading">Review, approval, and governance</h4>
            <p data-cnrisk-governance-summary>No governance workflow started.</p>
            <div class="cnrisk-workspace__actions">
              <button type="button" data-cnrisk-start-governance>Start standard workflow</button>
            </div>
            <div class="cnrisk-workspace__two">
              <label><span>Review stage</span><select data-cnrisk-assignment-stage><option>intake</option><option>domain</option><option>editorial</option><option>legal</option><option>compliance</option><option>final</option></select></label>
              <label><span>Reviewer role</span><select data-cnrisk-reviewer-role><option value="reviewer">Reviewer</option><option value="domain_reviewer">Domain reviewer</option><option value="editorial_reviewer">Editorial reviewer</option><option value="legal_reviewer">Legal reviewer</option><option value="compliance_reviewer">Compliance reviewer</option><option value="final_approver">Final approver</option></select></label>
              <label><span>Reviewer identifier</span><input data-cnrisk-reviewer-id placeholder="reviewer@example.org" /></label>
              <label><span>Due date</span><input type="datetime-local" data-cnrisk-assignment-due /></label>
            </div>
            <button type="button" data-cnrisk-assign-reviewer>Assign reviewer</button>
            <div data-cnrisk-governance-assignments></div>
            <hr />
            <div class="cnrisk-workspace__two">
              <label><span>Decision stage</span><select data-cnrisk-decision-stage><option>intake</option><option>domain</option><option>editorial</option><option>legal</option><option>compliance</option><option>final</option></select></label>
              <label><span>Disposition</span><select data-cnrisk-disposition><option value="approve">Approve stage</option><option value="approve_with_conditions">Approve with conditions</option><option value="revise">Require revision</option><option value="reject">Reject</option><option value="waive">Waive stage</option></select></label>
              <label><span>Decision maker</span><input data-cnrisk-decided-by placeholder="reviewer@example.org" /></label>
              <label><span>Decision-maker role</span><select data-cnrisk-decider-role><option value="reviewer">Reviewer</option><option value="domain_reviewer">Domain reviewer</option><option value="editorial_reviewer">Editorial reviewer</option><option value="legal_reviewer">Legal reviewer</option><option value="compliance_reviewer">Compliance reviewer</option><option value="final_approver">Final approver</option><option value="administrator">Administrator</option></select></label>
            </div>
            <label><span>Rationale</span><textarea rows="2" data-cnrisk-decision-rationale></textarea></label>
            <label><span>Conditions, one per line</span><textarea rows="2" data-cnrisk-conditions></textarea></label>
            <label><span>Required wording, one per line</span><textarea rows="2" data-cnrisk-required-wording></textarea></label>
            <label><span>Publication restrictions</span><select multiple data-cnrisk-publication-restrictions><option value="internal_only">Internal only</option><option value="embargoed">Embargoed</option><option value="no_public_claim">No public claim</option><option value="attribution_required">Attribution required</option><option value="legal_review_required">Legal review required</option><option value="disclosure_required">Disclosure required</option></select></label>
            <label><span>Disclosures, one per line</span><textarea rows="2" data-cnrisk-disclosures></textarea></label>
            <div class="cnrisk-workspace__two">
              <label><span>Approval valid until</span><input type="datetime-local" data-cnrisk-valid-until /></label>
              <label><span>Reassess at</span><input type="datetime-local" data-cnrisk-reassessment-at /></label>
            </div>
            <button type="button" data-cnrisk-add-decision>Record governance decision</button>
            <div data-cnrisk-governance-decisions></div>
          </section>
          <section class="cnrisk-workspace__governance cnrisk-workspace__monitoring" aria-labelledby="cnrisk-monitoring-heading">
            <h4 id="cnrisk-monitoring-heading">Narrative change, freshness, and monitoring</h4>
            <p data-cnrisk-monitoring-summary>No monitoring snapshots or watches yet.</p>
            <div class="cnrisk-workspace__two">
              <label><span>Watch name</span><input data-cnrisk-watch-name value="Narrative change watch" /></label>
              <label><span>Cadence</span><select data-cnrisk-watch-cadence><option value="manual">Manual</option><option value="daily" selected>Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label>
            </div>
            <div class="cnrisk-workspace__actions">
              <button type="button" data-cnrisk-capture-snapshot>Capture snapshot</button>
              <button type="button" data-cnrisk-create-watch>Create watch</button>
              <button type="button" data-cnrisk-run-watch>Run monitoring check</button>
            </div>
            <div data-cnrisk-monitoring-detail></div>
          </section>
          <section class="cnrisk-workspace__governance cnrisk-workspace__stakeholders" aria-labelledby="cnrisk-stakeholder-heading">
            <h4 id="cnrisk-stakeholder-heading">Stakeholder, incentive, and pressure intelligence</h4>
            <p data-cnrisk-stakeholder-summary>No stakeholder records yet.</p>
            <p><small>Record observable actors, relationships, incentives, pressures, and consequences. The advisory summary does not infer hidden motives or change the analytical score automatically.</small></p>
            <h5>Add stakeholder</h5>
            <div class="cnrisk-workspace__two">
              <label><span>Name</span><input data-cnrisk-actor-name placeholder="Organization, community, or person" /></label>
              <label><span>Actor type</span><select data-cnrisk-actor-type><option value="organization">Organization</option><option value="individual">Individual</option><option value="community">Community</option><option value="company">Company</option><option value="government">Government</option><option value="regulator">Regulator</option><option value="funder">Funder</option><option value="media">Media</option><option value="research_institution">Research institution</option><option value="advocacy_group">Advocacy group</option><option value="public">Public</option><option value="other">Other</option></select></label>
              <label><span>Influence</span><select data-cnrisk-actor-influence><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label>
              <label><span>Stance</span><select data-cnrisk-actor-stance><option>supportive</option><option>neutral</option><option>opposed</option><option>mixed</option><option selected>unknown</option></select></label>
              <label><span>Disclosure status</span><select data-cnrisk-actor-disclosure><option>not_required</option><option>disclosed</option><option>partially_disclosed</option><option>not_disclosed</option><option selected>unknown</option></select></label>
              <label><span>Interests, one per line</span><textarea rows="2" data-cnrisk-actor-interests></textarea></label>
            </div>
            <label><span>Description</span><textarea rows="2" data-cnrisk-actor-description></textarea></label>
            <button type="button" data-cnrisk-add-actor>Add stakeholder</button>
            <hr />
            <h5>Add relationship</h5>
            <div class="cnrisk-workspace__two">
              <label><span>Source actor</span><select data-cnrisk-actor-select data-cnrisk-relationship-source><option value="">Select stakeholder</option></select></label>
              <label><span>Target actor</span><select data-cnrisk-actor-select data-cnrisk-relationship-target><option value="">Select stakeholder</option></select></label>
              <label><span>Relationship type</span><select data-cnrisk-relationship-type><option>funds</option><option>employs</option><option>governs</option><option>regulates</option><option>represents</option><option>advises</option><option>partners_with</option><option>competes_with</option><option>depends_on</option><option>supplies</option><option>influences</option><option>amplifies</option><option>contests</option><option>benefits_from</option><option>harmed_by</option><option selected>other</option></select></label>
              <label><span>Strength</span><select data-cnrisk-relationship-strength><option>low</option><option>medium</option><option>high</option><option>critical</option><option selected>unknown</option></select></label>
            </div>
            <label><span>Relationship description</span><textarea rows="2" data-cnrisk-relationship-description></textarea></label>
            <button type="button" data-cnrisk-add-relationship>Add relationship</button>
            <hr />
            <h5>Add incentive</h5>
            <div class="cnrisk-workspace__two">
              <label><span>Stakeholder</span><select data-cnrisk-actor-select data-cnrisk-incentive-actor><option value="">Select stakeholder</option></select></label>
              <label><span>Type</span><select data-cnrisk-incentive-type><option>financial</option><option>political</option><option>reputational</option><option>legal</option><option>social</option><option>operational</option><option>mission</option><option>career</option><option>ideological</option><option selected>other</option></select></label>
              <label><span>Magnitude</span><select data-cnrisk-incentive-magnitude><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label>
              <label><span>Alignment</span><select data-cnrisk-incentive-alignment><option>aligned</option><option>mixed</option><option>opposed</option><option selected>unknown</option></select></label>
              <label><span>Conflict status</span><select data-cnrisk-incentive-conflict><option>none</option><option>potential</option><option>managed</option><option selected>unknown</option></select></label>
              <label><span><input type="checkbox" data-cnrisk-incentive-disclosed /> Disclosed</span></label>
            </div>
            <label><span>Incentive description</span><textarea rows="2" data-cnrisk-incentive-description></textarea></label>
            <button type="button" data-cnrisk-add-incentive>Add incentive</button>
            <hr />
            <h5>Add pressure</h5>
            <div class="cnrisk-workspace__two">
              <label><span>Stakeholder</span><select data-cnrisk-actor-select data-cnrisk-pressure-actor><option value="">Select stakeholder</option></select></label>
              <label><span>Type</span><select data-cnrisk-pressure-type><option>financial</option><option>political</option><option>reputational</option><option>legal</option><option>social</option><option>operational</option><option>deadline</option><option>funding</option><option>media</option><option>public</option><option selected>other</option></select></label>
              <label><span>Intensity</span><select data-cnrisk-pressure-intensity><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label>
              <label><span>Time horizon</span><select data-cnrisk-pressure-horizon><option>immediate</option><option>short_term</option><option>medium_term</option><option>long_term</option><option selected>ongoing</option></select></label>
            </div>
            <label><span>Pressure description</span><textarea rows="2" data-cnrisk-pressure-description></textarea></label>
            <button type="button" data-cnrisk-add-pressure>Add pressure</button>
            <hr />
            <h5>Add consequence</h5>
            <div class="cnrisk-workspace__two">
              <label><span>Stakeholder</span><select data-cnrisk-actor-select data-cnrisk-consequence-actor><option value="">Select stakeholder</option></select></label>
              <label><span>Impact type</span><select data-cnrisk-consequence-type><option>financial</option><option>reputational</option><option>legal</option><option>operational</option><option>social</option><option>environmental</option><option>political</option><option>health</option><option>safety</option><option>rights</option><option selected>other</option></select></label>
              <label><span>Direction</span><select data-cnrisk-consequence-direction><option>benefit</option><option>harm</option><option>mixed</option><option selected>unknown</option></select></label>
              <label><span>Severity</span><select data-cnrisk-consequence-severity><option>low</option><option selected>moderate</option><option>high</option><option>critical</option></select></label>
            </div>
            <label><span>Consequence description</span><textarea rows="2" data-cnrisk-consequence-description></textarea></label>
            <button type="button" data-cnrisk-add-consequence>Add consequence</button>
            <div data-cnrisk-stakeholder-detail></div>
          </section>
          <section class="cnrisk-workspace__governance cnrisk-workspace__comparative" aria-labelledby="cnrisk-comparative-heading">
            <h4 id="cnrisk-comparative-heading">Comparative narratives and scenario analysis</h4>
            <p data-cnrisk-comparative-summary>No comparison set created.</p>
            <p><small>Compare immutable revisions, inspect claim-and-evidence divergence, stress-test explicit assumptions, and export an advisory Decision Studio handoff. No scenario is selected automatically.</small></p>
            <div class="cnrisk-workspace__two">
              <label><span>Comparison title</span><input data-cnrisk-comparison-title value="Comparative narrative review" /></label>
              <label><span>Scenario name</span><input data-cnrisk-scenario-name placeholder="Adversarial evidence challenge" /></label>
              <label><span>Scenario type</span><select data-cnrisk-scenario-type><option value="best_case">Best case</option><option value="base_case">Base case</option><option value="worst_case">Worst case</option><option value="counterfactual">Counterfactual</option><option value="adversarial" selected>Adversarial</option><option value="custom">Custom</option></select></label>
              <label><span>Scenario assumptions, one per line</span><textarea rows="2" data-cnrisk-scenario-assumptions></textarea></label>
            </div>
            <div class="cnrisk-workspace__actions">
              <button type="button" data-cnrisk-create-comparison>Create comparison from latest revisions</button>
              <button type="button" data-cnrisk-add-scenario>Evaluate scenario</button>
              <button type="button" data-cnrisk-run-sensitivity>Run sensitivity</button>
              <button type="button" data-cnrisk-decision-studio-handoff>Export Decision Studio handoff</button>
            </div>
            <div data-cnrisk-comparative-detail></div>
          </section>
          <div class="cnrisk-workspace__reviews">
            <label><span>Add review comment</span><textarea rows="2" data-cnrisk-review-body></textarea></label>
            <button type="button" data-cnrisk-add-review>Add review activity</button>
          </div>
        </main>
      </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('catalyst_narrative_risk_workspace', 'cnrisk_workspace_shortcode');


function cnrisk_public_brief_shortcode($atts = array()) {
    $atts = shortcode_atts(array(
        'title' => 'Narrative Risk Briefing',
        'claim' => 'No public claim was supplied.',
        'score' => '—',
        'level' => 'Not assessed',
        'evidence' => 'See the governed publication package for evidence details.',
        'governance' => 'Publication-approved narrative risk briefing.',
        'disclosure' => '',
        'reassessment' => 'Not scheduled',
    ), $atts, 'catalyst_narrative_risk_public_brief');
    wp_enqueue_style('cnrisk-publication-css');
    ob_start();
    ?>
    <article class="cnrisk-public-brief" data-cnrisk-public-brief>
      <header class="cnrisk-public-brief__head">
        <p class="cnrisk-publication__eyebrow">Governed public briefing</p>
        <h2><?php echo esc_html($atts['title']); ?></h2>
        <div class="cnrisk-public-brief__meta"><span>Risk score: <?php echo esc_html($atts['score']); ?></span><span>Level: <?php echo esc_html($atts['level']); ?></span></div>
      </header>
      <section class="cnrisk-public-brief__section"><h3>Claim</h3><p><?php echo esc_html($atts['claim']); ?></p></section>
      <section class="cnrisk-public-brief__section"><h3>Evidence</h3><p><?php echo esc_html($atts['evidence']); ?></p></section>
      <section class="cnrisk-public-brief__section"><h3>Governance</h3><p><?php echo esc_html($atts['governance']); ?></p></section>
      <?php if ($atts['disclosure'] !== '') : ?><section class="cnrisk-public-brief__section"><h3>Disclosure</h3><p><?php echo esc_html($atts['disclosure']); ?></p></section><?php endif; ?>
      <section class="cnrisk-public-brief__section"><h3>Reassessment</h3><p><?php echo esc_html($atts['reassessment']); ?></p></section>
    </article>
    <?php
    return ob_get_clean();
}
add_shortcode('catalyst_narrative_risk_public_brief', 'cnrisk_public_brief_shortcode');

function cnrisk_publication_workspace_shortcode() {
    wp_enqueue_style('cnrisk-publication-css');
    wp_enqueue_script('cnrisk-publication-js');
    ob_start();
    ?>
    <section class="cnrisk-publication" data-cnrisk-publication>
      <header class="cnrisk-publication__head"><p class="cnrisk-publication__eyebrow">Publication studio</p><h3>Narrative Risk Briefing and Publication</h3><p>Prepare a public-safe preview after the institutional API has confirmed governance approval, conditions, disclosures, and reassessment dates.</p></header>
      <div class="cnrisk-publication__grid">
        <form>
          <label><span>Briefing title</span><input name="title" value="Governed Narrative Risk Briefing" required /></label>
          <label><span>Reviewed claim</span><textarea name="claim" rows="4" required>Available evidence indicates the initiative may improve public trust.</textarea></label>
          <div class="cnrisk-publication__grid"><label><span>Risk score</span><input name="risk_score" type="number" min="0" value="18" /></label><label><span>Risk level</span><select name="risk_level"><option>low</option><option selected>moderate</option><option>high</option><option>critical</option></select></label></div>
          <label><span>Evidence summary</span><textarea name="evidence_summary" rows="3">Evidence coverage, source independence, contradictions, and freshness are described in the checksummed publication package.</textarea></label>
          <label><span>Governance status</span><input name="governance_status" value="Approved with conditions; publication allowed." /></label>
          <label><span>Required wording, one per line</span><textarea name="required_wording" rows="2">Available evidence indicates</textarea></label>
          <label><span>Disclosures, one per line</span><textarea name="disclosures" rows="2">This assessment reflects evidence available on July 17, 2026.</textarea></label>
          <label><span>Reassessment date</span><input name="reassessment_at" type="datetime-local" /></label>
          <div class="cnrisk-publication__actions"><button type="submit">Build preview</button><button type="button" data-cnrisk-download-format="markdown">Markdown</button><button type="button" data-cnrisk-download-format="html">HTML</button><button type="button" data-cnrisk-download-format="json">JSON</button></div>
        </form>
        <div class="cnrisk-publication__preview" data-cnrisk-publication-preview aria-live="polite"></div>
      </div>
      <p class="cnrisk-publication__notice">Browser preview mode does not approve publication. Production publishing, PDF/CSV/JSON-LD exports, API scopes, embeds, and platform handoffs are governed by the v1.10.0 REST workspace.</p>
    </section>
    <?php
    return ob_get_clean();
}
add_shortcode('catalyst_narrative_risk_publication_workspace', 'cnrisk_publication_workspace_shortcode');

/**
 * Render an accessible production-readiness checklist for administrators.
 */
function cnrisk_readiness_shortcode() {
    wp_enqueue_style('cnrisk-workspace-css');
    ob_start();
    ?>
    <section class="cnrisk-readiness" data-cnrisk-readiness aria-labelledby="cnrisk-readiness-title">
      <header class="cnrisk-readiness__head">
        <p class="cnrisk-demo__eyebrow">Production hardening</p>
        <h3 id="cnrisk-readiness-title">Narrative Risk deployment readiness</h3>
        <p>Use this operator checklist with the REST or command-line readiness report before enabling production access.</p>
      </header>
      <div class="cnrisk-readiness__grid" role="list" aria-label="Production readiness domains">
        <article role="listitem"><h4>Security</h4><p>Require scoped API access, HTTPS, secure headers, an explicit origin allowlist, request limits, and strong administrator credentials.</p></article>
        <article role="listitem"><h4>Privacy</h4><p>Activate a retention policy, document encryption at rest, review legal holds, and assess each case before disposition.</p></article>
        <article role="listitem"><h4>Recovery</h4><p>Create a protected SQLite backup, verify its checksum and integrity, and complete a restore drill outside the live database.</p></article>
        <article role="listitem"><h4>Accessibility</h4><p>Validate labels, keyboard focus, motion preferences, semantic headings, controls, contrast, and responsive behavior.</p></article>
        <article role="listitem"><h4>Performance</h4><p>Keep health, case listing, bundle generation, bundle size, and database size within the declared release budgets.</p></article>
      </div>
      <p class="cnrisk-readiness__boundary"><strong>Boundary:</strong> A readiness report documents explicit controls; it does not certify that a deployment is secure.</p>
    </section>
    <?php
    return ob_get_clean();
}
add_shortcode('catalyst_narrative_risk_readiness', 'cnrisk_readiness_shortcode');
