<?php
/**
 * Plugin Name: Catalyst Narrative Risk
 * Description: Narrative-risk scoring, evidence ledger, claim decomposition, narrative mapping, and persistent review workspace interfaces for Sustainable Catalyst.
 * Version: 1.5.0
 * Author: Content Catalyst LLC
 * License: MIT
 */

if (!defined('ABSPATH')) {
    exit;
}

function cnrisk_demo_assets() {
    $base = plugin_dir_url(__FILE__);
    wp_register_style('cnrisk-demo-css', $base . 'assets/catalyst-narrative-risk-demo.css', array(), '1.5.0');
    wp_register_script('cnrisk-method-js', $base . 'assets/narrative-risk-method.js', array(), '1.5.0', true);
    wp_register_script('cnrisk-map-js', $base . 'assets/narrative-risk-map.js', array(), '1.5.0', true);
    wp_register_script('cnrisk-engine-js', $base . 'assets/narrative-risk-engine.js', array('cnrisk-method-js', 'cnrisk-map-js'), '1.5.0', true);
    wp_register_script('cnrisk-demo-js', $base . 'assets/catalyst-narrative-risk-demo.js', array('cnrisk-engine-js'), '1.5.0', true);
    wp_register_style('cnrisk-workspace-css', $base . 'assets/catalyst-narrative-risk-workspace.css', array(), '1.5.0');
    wp_register_script('cnrisk-workspace-js', $base . 'assets/catalyst-narrative-risk-workspace.js', array('cnrisk-engine-js'), '1.5.0', true);
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
        <p>Create durable cases, add immutable analytical revisions, assign staged reviews, record approval conditions, and export checksummed governance bundles.</p>
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
            Browser mode stores cases locally on this device. Institutional deployments should connect the interface to the v1.5.0 SQLite-backed REST workspace API.
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
