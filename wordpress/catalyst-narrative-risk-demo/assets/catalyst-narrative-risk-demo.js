(function () {
  'use strict';
  const engine = window.CatalystNarrativeRiskEngine;
  if (!engine) return;

  const sampleLedger = {
    claims: [
      {
        text: 'Independent measurements indicate the pilot reduced energy use by approximately 12 percent.',
        claim_type: 'factual',
        role: 'primary',
        notes: 'Limited to the pilot sites and measured period.'
      }
    ],
    sources: [
      {
        title: 'Pilot meter audit',
        source_type: 'peer_reviewed_or_audited',
        creators: ['Energy Audit Team'],
        publisher: 'Independent Audit Group',
        published_year: 2026,
        url: 'https://example.org/pilot-audit',
        accessed_at: '2026-07-17T12:00:00+00:00',
        identifiers: [{ scheme: 'doi', value: '10.0000/example.audit' }],
        independence_group: 'independent-audit-group',
        directness: 'direct',
        freshness: 'current',
        provenance: { acquisition_method: 'document_import', imported_from: 'knowledge-library:pilot-meter-audit', imported_at: '2026-07-17T12:00:00+00:00', content_sha256: null },
        notes: 'Independent audit of weather-normalized meter data.'
      },
      {
        title: 'Utility interval dataset',
        source_type: 'official_or_primary',
        creators: ['City Utility'],
        publisher: 'City Utility',
        published_year: 2026,
        url: 'https://example.org/utility-data',
        accessed_at: '2026-07-17T12:00:00+00:00',
        identifiers: [{ scheme: 'catalog', value: 'dataset:utility-interval-2026' }],
        independence_group: 'city-utility',
        directness: 'direct',
        freshness: 'current',
        provenance: { acquisition_method: 'catalyst_data', imported_from: 'catalyst-data:utility-interval-2026', imported_at: '2026-07-17T12:00:00+00:00', content_sha256: null },
        notes: 'Primary interval readings used by the audit.'
      }
    ]
  };

  function hydrateSampleLedger() {
    const claims = JSON.parse(JSON.stringify(sampleLedger.claims));
    const sources = JSON.parse(JSON.stringify(sampleLedger.sources));
    const normalized = engine.scoreNarrativeRisk({
      claim: claims[0].text,
      claims: claims,
      sources: sources,
      evidence_items: [],
      relationships: []
    }).evidence_ledger;
    const claimId = normalized.claims[0].claim_id;
    const sourceIds = normalized.sources.map(function (source) { return source.source_id; });
    const evidenceItems = [
      {
        source_id: sourceIds[0], evidence_type: 'finding',
        excerpt: 'Weather-normalized consumption declined 11.8 percent across the pilot sites.',
        locator: 'p. 14', captured_at: '2026-07-17T12:05:00+00:00', notes: 'Audited finding.'
      },
      {
        source_id: sourceIds[1], evidence_type: 'data',
        excerpt: 'The interval dataset shows a 12.1 percent reduction relative to the normalized baseline.',
        locator: 'dataset row 18', captured_at: '2026-07-17T12:06:00+00:00', notes: 'Primary data corroboration.'
      }
    ];
    const normalizedWithEvidence = engine.scoreNarrativeRisk({
      claim: claims[0].text, claims: claims, sources: sources, evidence_items: evidenceItems, relationships: []
    }).evidence_ledger;
    return {
      claims: claims,
      sources: sources,
      evidence_items: evidenceItems,
      relationships: normalizedWithEvidence.evidence_items.map(function (evidence, index) {
        return {
          claim_id: claimId,
          evidence_id: evidence.evidence_id,
          relation_type: 'support',
          strength: 'strong',
          notes: index === 0 ? 'Direct audited finding.' : 'Independent primary-data corroboration.'
        };
      })
    };
  }

  function readForm(form) {
    const payload = Object.fromEntries(new FormData(form).entries());
    const ledgerText = String(payload.evidence_ledger_json || '').trim();
    const mapText = String(payload.narrative_map_json || '').trim();
    delete payload.evidence_ledger_json;
    delete payload.narrative_map_json;
    if (ledgerText) {
      let ledger;
      try {
        ledger = JSON.parse(ledgerText);
      } catch (error) {
        throw new Error('Evidence ledger JSON is invalid: ' + error.message);
      }
      if (!ledger || Array.isArray(ledger) || typeof ledger !== 'object') {
        throw new Error('Evidence ledger JSON must be an object containing claims, sources, evidence_items, and relationships.');
      }
      ['claims', 'sources', 'evidence_items', 'relationships'].forEach(function (field) {
        if (ledger[field] !== undefined) payload[field] = ledger[field];
      });
      delete payload.source_type;
      delete payload.evidence_strength;
      delete payload.source_count;
    }
    if (mapText) {
      let narrativeMap;
      try { narrativeMap = JSON.parse(mapText); }
      catch (error) { throw new Error('Narrative map JSON is invalid: ' + error.message); }
      if (!narrativeMap || Array.isArray(narrativeMap) || typeof narrativeMap !== 'object') {
        throw new Error('Narrative map JSON must be an object containing narrative_nodes, narrative_links, wording_variants, and selected_variant_id.');
      }
      ['narrative_nodes', 'narrative_links', 'wording_variants', 'selected_variant_id'].forEach(function (field) {
        if (narrativeMap[field] !== undefined) payload[field] = narrativeMap[field];
      });
    }
    return payload;
  }

  function list(element, items, emptyText) {
    element.innerHTML = '';
    const values = items.length ? items : [emptyText || 'None recorded.'];
    values.forEach(function (text) {
      const item = document.createElement('li');
      item.textContent = text;
      element.appendChild(item);
    });
  }

  function render(root, record) {
    const calculations = record.calculations;
    const interpretation = record.interpretation;
    const ledger = record.evidence_ledger;
    const narrativeMap = record.narrative_map;
    const coverage = ledger.coverage.overall;
    root._cnriskRecord = record;
    root.querySelector('[data-cnrisk-error]').hidden = true;
    root.querySelector('[data-cnrisk-score]').textContent = calculations.risk_score + ' / 100';
    root.querySelector('[data-cnrisk-level]').textContent = interpretation.risk_level + ' narrative risk';
    root.querySelector('[data-cnrisk-meter]').style.width = calculations.risk_score + '%';
    root.querySelector('[data-cnrisk-note]').textContent = interpretation.decision_note;
    root.querySelector('[data-cnrisk-identity]').textContent =
      record.identifiers.record_id + ' · method ' + record.method_snapshot.method_version + ' · schema ' + record.contract.contract_version;
    root.querySelector('[data-cnrisk-human]').textContent =
      record.human_decision.status.replaceAll('_', ' ') + ' · ' + record.human_decision.disposition.replaceAll('_', ' ');
    root.querySelector('[data-cnrisk-coverage]').textContent =
      coverage.coverage_status + ' · ' + coverage.claim_count + ' claim(s) · ' + coverage.source_count +
      ' source(s) · ' + coverage.evidence_count + ' evidence item(s) · ' + coverage.independent_source_count + ' independent source group(s)';
    root.querySelector('[data-cnrisk-derived]').textContent =
      ledger.derived_scoring_inputs.source_type.replaceAll('_', ' ') + ' · ' +
      ledger.derived_scoring_inputs.evidence_strength + ' evidence · ' +
      ledger.derived_scoring_inputs.source_count + ' linked source(s)';
    list(root.querySelector('[data-cnrisk-sources]'), ledger.source_list.map(function (source) { return source.citation; }), 'No item-level sources recorded.');
    root.querySelector('[data-cnrisk-map-summary]').textContent =
      narrativeMap.analysis.summary.map_status.replaceAll('_', ' ') + ' · ' + narrativeMap.analysis.summary.node_count +
      ' node(s) · ' + narrativeMap.analysis.summary.link_count + ' link(s) · ' +
      narrativeMap.analysis.summary.issue_count + ' diagnostic issue(s)';
    list(root.querySelector('[data-cnrisk-map-issues]'), narrativeMap.analysis.issues.map(function (issue) {
      return issue.severity.toUpperCase() + ' · ' + issue.message;
    }), 'No narrative-map diagnostics generated.');
    list(root.querySelector('[data-cnrisk-flags]'), interpretation.flags, 'No flags generated.');
    list(root.querySelector('[data-cnrisk-actions]'), interpretation.review_actions, 'No actions generated.');
    root.querySelector('[data-cnrisk-json]').textContent = JSON.stringify(record, null, 2);

    const bars = root.querySelector('[data-cnrisk-bars]');
    bars.innerHTML = '';
    Object.entries(calculations.components).forEach(function (entry) {
      const key = entry[0];
      const component = entry[1];
      const item = document.createElement('div');
      const header = document.createElement('header');
      const label = document.createElement('span');
      const weight = document.createElement('strong');
      const track = document.createElement('div');
      const fill = document.createElement('span');
      item.className = 'cnrisk-demo__bar';
      item.title = component.rationale + ' ' + component.remediation;
      label.textContent = key.replaceAll('_', ' ') + ' · ' + component.input_value;
      weight.textContent = String(component.weight);
      fill.style.width = Math.min(100, component.weight * 4) + '%';
      header.append(label, weight);
      track.appendChild(fill);
      item.append(header, track);
      bars.appendChild(item);
    });
  }

  function renderError(root, error) {
    root._cnriskRecord = null;
    const errorBox = root.querySelector('[data-cnrisk-error]');
    errorBox.textContent = error.message || 'Unable to generate a narrative-risk record.';
    errorBox.hidden = false;
  }

  function generate(root, form) {
    try {
      const record = engine.buildNarrativeRiskRecord(readForm(form));
      render(root, record);
      return record;
    } catch (error) {
      renderError(root, error);
      return null;
    }
  }

  function init(root) {
    const form = root.querySelector('[data-cnrisk-form]');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      generate(root, form);
    });
    root.querySelector('[data-cnrisk-sample]').addEventListener('click', function () {
      const ledger = hydrateSampleLedger();
      form.claim.value = ledger.claims[0].text;
      form.uncertainty.value = 'medium';
      form.review_status.value = 'partly_reviewed';
      form.narrative_volatility.value = 'low';
      form.stakeholder_pressure.value = 'medium';
      form.time_sensitivity.value = 'medium';
      form.consequences.value = 'high';
      form.method_notes.value = 'Use only within the measured pilot boundary and retain the weather-normalization assumptions.';
      form.evidence_ledger_json.value = JSON.stringify(ledger, null, 2);
      form.narrative_map_json.value = '';
      generate(root, form);
    });
    root.querySelector('[data-cnrisk-download]').addEventListener('click', function () {
      const record = root._cnriskRecord || generate(root, form);
      if (!record) return;
      const blob = new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'catalyst-narrative-risk-record-v1.9.0.json';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    });
    generate(root, form);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-cnrisk-demo]').forEach(init);
  });
})();
