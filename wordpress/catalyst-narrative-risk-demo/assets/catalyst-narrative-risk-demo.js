(function () {
  'use strict';
  const engine = window.CatalystNarrativeRiskEngine;
  if (!engine) return;

  function readForm(form) {
    const input = Object.fromEntries(new FormData(form).entries());
    return input;
  }

  function list(element, items) {
    element.innerHTML = '';
    items.forEach(function (text) {
      const item = document.createElement('li');
      item.textContent = text;
      element.appendChild(item);
    });
  }

  function render(root, record) {
    root._cnriskRecord = record;
    root.querySelector('[data-cnrisk-error]').hidden = true;
    root.querySelector('[data-cnrisk-score]').textContent = record.risk_score + ' / 100';
    root.querySelector('[data-cnrisk-level]').textContent = record.risk_level + ' narrative risk';
    root.querySelector('[data-cnrisk-meter]').style.width = record.risk_score + '%';
    root.querySelector('[data-cnrisk-note]').textContent = record.decision_note;
    list(root.querySelector('[data-cnrisk-flags]'), record.flags);
    list(root.querySelector('[data-cnrisk-actions]'), record.review_actions);
    root.querySelector('[data-cnrisk-json]').textContent = JSON.stringify(record, null, 2);

    const bars = root.querySelector('[data-cnrisk-bars]');
    bars.innerHTML = '';
    Object.entries(record.components).forEach(function (entry) {
      const key = entry[0];
      const value = entry[1];
      const item = document.createElement('div');
      const header = document.createElement('header');
      const label = document.createElement('span');
      const weight = document.createElement('strong');
      const track = document.createElement('div');
      const fill = document.createElement('span');
      item.className = 'cnrisk-demo__bar';
      label.textContent = key.replaceAll('_', ' ');
      weight.textContent = String(value);
      fill.style.width = Math.min(100, value * 4) + '%';
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
      form.claim.value = 'A new sustainability initiative will materially improve public trust within one year.';
      form.source_type.value = 'reputable_secondary';
      form.evidence_strength.value = 'limited';
      form.source_count.value = 2;
      form.uncertainty.value = 'high';
      form.review_status.value = 'partly_reviewed';
      form.narrative_volatility.value = 'medium';
      form.stakeholder_pressure.value = 'high';
      form.time_sensitivity.value = 'medium';
      form.consequences.value = 'high';
      form.method_notes.value = 'Claim needs narrower language, stronger baseline evidence, and a review date before publication.';
      generate(root, form);
    });
    root.querySelector('[data-cnrisk-download]').addEventListener('click', function () {
      const record = root._cnriskRecord || generate(root, form);
      if (!record) return;
      const blob = new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'catalyst-narrative-risk-record.json';
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
