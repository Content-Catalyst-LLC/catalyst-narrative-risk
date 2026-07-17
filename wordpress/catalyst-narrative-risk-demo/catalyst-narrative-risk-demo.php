<?php
/**
 * Plugin Name: Catalyst Narrative Risk Demo
 * Description: Browser-based Sustainable Catalyst Narrative Risk demo with shortcode [catalyst_narrative_risk_demo].
 * Version: 1.2.0
 * Author: Content Catalyst LLC
 * License: MIT
 */

if (!defined('ABSPATH')) {
    exit;
}

function cnrisk_demo_assets() {
    $base = plugin_dir_url(__FILE__);
    wp_register_style('cnrisk-demo-css', $base . 'assets/catalyst-narrative-risk-demo.css', array(), '1.2.0');
    wp_register_script('cnrisk-method-js', $base . 'assets/narrative-risk-method.js', array(), '1.2.0', true);
    wp_register_script('cnrisk-engine-js', $base . 'assets/narrative-risk-engine.js', array('cnrisk-method-js'), '1.2.0', true);
    wp_register_script('cnrisk-demo-js', $base . 'assets/catalyst-narrative-risk-demo.js', array('cnrisk-engine-js'), '1.2.0', true);
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
        <p>Build a traceable review record linking claims to sources, evidence excerpts, provenance, uncertainty, and human judgment.</p>
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
