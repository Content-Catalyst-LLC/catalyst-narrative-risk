(function () {
  const sourceWeights = {
    official_or_primary: 0,
    peer_reviewed_or_audited: 3,
    reputable_secondary: 8,
    internal_unreviewed: 14,
    single_report_or_media: 18,
    social_or_anecdotal: 24,
    unknown: 28
  };
  const evidenceWeights = { strong: 0, moderate: 10, limited: 20, weak: 30, unclear: 24 };
  const scaleWeights = { low: 3, medium: 10, high: 18 };
  const consequenceWeights = { low: 3, moderate: 10, high: 18, critical: 24 };
  const reviewWeights = { reviewed: 0, partly_reviewed: 8, not_reviewed: 18 };

  function sourceCountPenalty(n) {
    n = Number(n || 0);
    if (n <= 0) return 22;
    if (n === 1) return 16;
    if (n === 2) return 8;
    if (n <= 4) return 3;
    return 0;
  }
  function clamp(n) { return Math.max(0, Math.min(100, Math.round(n))); }
  function level(score) { return score >= 70 ? 'High' : (score >= 40 ? 'Medium' : 'Low'); }

  function flags(input, score) {
    const out = [];
    if (input.source_count <= 1) out.push('Single-source or under-sourced claim');
    if (['weak', 'limited', 'unclear'].includes(input.evidence_strength)) out.push('Evidence does not yet support confident use');
    if (input.uncertainty === 'high') out.push('High uncertainty should be stated explicitly');
    if (input.narrative_volatility === 'high') out.push('Narrative may be changing quickly');
    if (input.stakeholder_pressure === 'high') out.push('Stakeholder pressure may be influencing interpretation');
    if (input.time_sensitivity === 'high') out.push('Time-sensitive claim requires recent source check');
    if (['high', 'critical'].includes(input.consequences)) out.push('High-consequence claim needs stricter review');
    if (input.review_status === 'not_reviewed') out.push('Claim has not completed review');
    if (!out.length && score < 40) out.push('No major heuristic risk flags');
    return out;
  }

  function actions(input) {
    const out = [];
    if (input.source_count <= 2) out.push('Add at least one independent source or primary reference.');
    if (['weak', 'limited', 'unclear'].includes(input.evidence_strength)) out.push('Rewrite claim with narrower language until evidence improves.');
    if (input.uncertainty === 'high') out.push('Add an uncertainty note that separates knowns, assumptions, and unknowns.');
    if (input.narrative_volatility === 'high' || input.time_sensitivity === 'high') out.push('Re-check source freshness before publication or decision use.');
    if (input.stakeholder_pressure === 'high') out.push('Document whether pressure, incentives, or reputational concerns may be shaping the claim.');
    if (['high', 'critical'].includes(input.consequences)) out.push('Escalate to domain, legal, compliance, or editorial review as appropriate.');
    if (input.review_status !== 'reviewed') out.push('Record a reviewer, date, and decision before treating the claim as approved.');
    if (!out.length) out.push('Maintain source links, method notes, and review date for future audit.');
    return out;
  }

  function decisionNote(lvl) {
    if (lvl === 'High') return 'Do not use as a confident public claim without additional review, source support, and narrowed language.';
    if (lvl === 'Medium') return 'Use cautiously with visible uncertainty, source links, and review notes.';
    return 'Risk appears lower by heuristic review, but source links and review date should still be preserved.';
  }

  function readForm(form) {
    const data = new FormData(form);
    const input = Object.fromEntries(data.entries());
    input.source_count = Number(input.source_count || 0);
    return input;
  }

  function score(input) {
    const components = {
      source_type: sourceWeights[input.source_type] || 0,
      evidence_strength: evidenceWeights[input.evidence_strength] || 10,
      uncertainty: scaleWeights[input.uncertainty] || 10,
      narrative_volatility: scaleWeights[input.narrative_volatility] || 10,
      stakeholder_pressure: scaleWeights[input.stakeholder_pressure] || 10,
      time_sensitivity: scaleWeights[input.time_sensitivity] || 10,
      consequences: consequenceWeights[input.consequences] || 10,
      review_status: reviewWeights[input.review_status] || 8,
      source_count: sourceCountPenalty(input.source_count)
    };
    const riskScore = clamp(Object.values(components).reduce((a, b) => a + b, 0) * 0.68);
    const riskLevel = level(riskScore);
    return {
      record_type: 'catalyst_narrative_risk_record',
      generated_at: new Date().toISOString(),
      claim: input.claim || '',
      risk_score: riskScore,
      risk_level: riskLevel,
      components,
      flags: flags(input, riskScore),
      review_actions: actions(input),
      decision_note: decisionNote(riskLevel),
      inputs: input,
      method: 'transparent heuristic scoring; not truth verification'
    };
  }

  function list(el, items) {
    el.innerHTML = '';
    items.forEach(text => {
      const li = document.createElement('li');
      li.textContent = text;
      el.appendChild(li);
    });
  }

  function render(root, record) {
    root._cnriskRecord = record;
    root.querySelector('[data-cnrisk-score]').textContent = record.risk_score + ' / 100';
    root.querySelector('[data-cnrisk-level]').textContent = record.risk_level + ' narrative risk';
    root.querySelector('[data-cnrisk-meter]').style.width = record.risk_score + '%';
    root.querySelector('[data-cnrisk-note]').textContent = record.decision_note;
    list(root.querySelector('[data-cnrisk-flags]'), record.flags);
    list(root.querySelector('[data-cnrisk-actions]'), record.review_actions);
    root.querySelector('[data-cnrisk-json]').textContent = JSON.stringify(record, null, 2);

    const bars = root.querySelector('[data-cnrisk-bars]');
    bars.innerHTML = '';
    Object.entries(record.components).forEach(([key, value]) => {
      const item = document.createElement('div');
      item.className = 'cnrisk-demo__bar';
      item.innerHTML = '<header><span>' + key.replaceAll('_', ' ') + '</span><strong>' + value + '</strong></header><div><span style="width:' + Math.min(100, value * 4) + '%"></span></div>';
      bars.appendChild(item);
    });
  }

  function init(root) {
    const form = root.querySelector('[data-cnrisk-form]');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      render(root, score(readForm(form)));
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
      render(root, score(readForm(form)));
    });
    root.querySelector('[data-cnrisk-download]').addEventListener('click', function () {
      const record = root._cnriskRecord || score(readForm(form));
      render(root, record);
      const blob = new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'catalyst-narrative-risk-record.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
    render(root, score(readForm(form)));
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-cnrisk-demo]').forEach(init);
  });
})();
