(function (root, factory) {
  const engine = factory();
  if (typeof module === 'object' && module.exports) module.exports = engine;
  if (root) root.CatalystNarrativeRiskEngine = engine;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = '1.0.1';
  const RECORD_TYPE = 'catalyst_narrative_risk_record';
  const METHOD = 'transparent heuristic scoring; not truth verification';
  const SCHEMA_VERSION = '1.0.1';
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
  const inputFields = new Set([
    'claim', 'source_type', 'evidence_strength', 'uncertainty',
    'narrative_volatility', 'stakeholder_pressure', 'time_sensitivity',
    'consequences', 'review_status', 'source_count', 'method_notes'
  ]);
  const hasOwn = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

  class NarrativeRiskValidationError extends Error {
    constructor(message) {
      super(message);
      this.name = 'NarrativeRiskValidationError';
    }
  }

  function cleanChoice(value, allowed, fallback) {
    if (typeof value !== 'string') return fallback;
    const cleaned = value.trim().toLowerCase();
    return hasOwn(allowed, cleaned) ? cleaned : fallback;
  }

  function cleanText(value, field, required) {
    if (value === null || typeof value === 'undefined') value = '';
    if (typeof value !== 'string') throw new NarrativeRiskValidationError(field + ' must be a string');
    const cleaned = value.trim();
    if (required && !cleaned) throw new NarrativeRiskValidationError(field + ' is required');
    return cleaned;
  }

  function cleanSourceCount(value) {
    if (value === null || typeof value === 'undefined' || value === '') return 0;
    let parsed;
    if (typeof value === 'number' && Number.isInteger(value)) {
      parsed = value;
    } else if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
      parsed = Number(value.trim());
    } else {
      throw new NarrativeRiskValidationError('source_count must be a non-negative integer');
    }
    if (!Number.isSafeInteger(parsed) || parsed < 0) {
      throw new NarrativeRiskValidationError('source_count must be a non-negative integer');
    }
    return parsed;
  }

  function normalizeInput(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new NarrativeRiskValidationError('payload must be a JSON object');
    }
    const unknown = Object.keys(payload).filter(key => !inputFields.has(key)).sort();
    if (unknown.length) throw new NarrativeRiskValidationError('unsupported input field(s): ' + unknown.join(', '));
    return {
      claim: cleanText(payload.claim, 'claim', true),
      source_type: cleanChoice(hasOwn(payload, 'source_type') ? payload.source_type : 'reputable_secondary', sourceWeights, 'reputable_secondary'),
      evidence_strength: cleanChoice(hasOwn(payload, 'evidence_strength') ? payload.evidence_strength : 'moderate', evidenceWeights, 'moderate'),
      uncertainty: cleanChoice(hasOwn(payload, 'uncertainty') ? payload.uncertainty : 'medium', scaleWeights, 'medium'),
      narrative_volatility: cleanChoice(hasOwn(payload, 'narrative_volatility') ? payload.narrative_volatility : 'medium', scaleWeights, 'medium'),
      stakeholder_pressure: cleanChoice(hasOwn(payload, 'stakeholder_pressure') ? payload.stakeholder_pressure : 'medium', scaleWeights, 'medium'),
      time_sensitivity: cleanChoice(hasOwn(payload, 'time_sensitivity') ? payload.time_sensitivity : 'medium', scaleWeights, 'medium'),
      consequences: cleanChoice(hasOwn(payload, 'consequences') ? payload.consequences : 'moderate', consequenceWeights, 'moderate'),
      review_status: cleanChoice(hasOwn(payload, 'review_status') ? payload.review_status : 'partly_reviewed', reviewWeights, 'partly_reviewed'),
      source_count: cleanSourceCount(hasOwn(payload, 'source_count') ? payload.source_count : 2),
      method_notes: cleanText(hasOwn(payload, 'method_notes') ? payload.method_notes : '', 'method_notes', false)
    };
  }

  function sourceCountPenalty(count) {
    if (count <= 0) return 22;
    if (count === 1) return 16;
    if (count === 2) return 8;
    if (count <= 4) return 3;
    return 0;
  }

  function clamp(value) { return Math.max(0, Math.min(100, Math.round(value))); }
  function level(score) { return score >= 70 ? 'High' : (score >= 40 ? 'Medium' : 'Low'); }

  function flags(input, score) {
    const output = [];
    if (input.source_count <= 1) output.push('Single-source or under-sourced claim');
    if (['weak', 'limited', 'unclear'].includes(input.evidence_strength)) output.push('Evidence does not yet support confident use');
    if (input.uncertainty === 'high') output.push('High uncertainty should be stated explicitly');
    if (input.narrative_volatility === 'high') output.push('Narrative may be changing quickly');
    if (input.stakeholder_pressure === 'high') output.push('Stakeholder pressure may be influencing interpretation');
    if (input.time_sensitivity === 'high') output.push('Time-sensitive claim requires recent source check');
    if (['high', 'critical'].includes(input.consequences)) output.push('High-consequence claim needs stricter review');
    if (input.review_status === 'not_reviewed') output.push('Claim has not completed review');
    if (!output.length && score < 40) output.push('No major heuristic risk flags');
    return output;
  }

  function reviewActions(input) {
    const output = [];
    if (input.source_count <= 2) output.push('Add at least one independent source or primary reference.');
    if (['weak', 'limited', 'unclear'].includes(input.evidence_strength)) output.push('Rewrite claim with narrower language until evidence improves.');
    if (input.uncertainty === 'high') output.push('Add an uncertainty note that separates knowns, assumptions, and unknowns.');
    if (input.narrative_volatility === 'high' || input.time_sensitivity === 'high') output.push('Re-check source freshness before publication or decision use.');
    if (input.stakeholder_pressure === 'high') output.push('Document whether pressure, incentives, or reputational concerns may be shaping the claim.');
    if (['high', 'critical'].includes(input.consequences)) output.push('Escalate to domain, legal, compliance, or editorial review as appropriate.');
    if (input.review_status !== 'reviewed') output.push('Record a reviewer, date, and decision before treating the claim as approved.');
    if (!output.length) output.push('Maintain source links, method notes, and review date for future audit.');
    return output;
  }

  function decisionNote(riskLevel) {
    if (riskLevel === 'High') return 'Do not use as a confident public claim without additional review, source support, and narrowed language.';
    if (riskLevel === 'Medium') return 'Use cautiously with visible uncertainty, source links, and review notes.';
    return 'Risk appears lower by heuristic review, but source links and review date should still be preserved.';
  }

  function scoreNarrativeRisk(payload) {
    const input = normalizeInput(payload);
    const components = {
      source_type: sourceWeights[input.source_type],
      evidence_strength: evidenceWeights[input.evidence_strength],
      uncertainty: scaleWeights[input.uncertainty],
      narrative_volatility: scaleWeights[input.narrative_volatility],
      stakeholder_pressure: scaleWeights[input.stakeholder_pressure],
      time_sensitivity: scaleWeights[input.time_sensitivity],
      consequences: consequenceWeights[input.consequences],
      review_status: reviewWeights[input.review_status],
      source_count: sourceCountPenalty(input.source_count)
    };
    const riskScore = clamp(Object.values(components).reduce((sum, value) => sum + value, 0) * 0.68);
    const riskLevel = level(riskScore);
    return {
      claim: input.claim,
      risk_score: riskScore,
      risk_level: riskLevel,
      components: components,
      flags: flags(input, riskScore),
      review_actions: reviewActions(input),
      decision_note: decisionNote(riskLevel),
      inputs: input
    };
  }

  function buildNarrativeRiskRecord(payload, generatedAt) {
    return Object.assign(scoreNarrativeRisk(payload), {
      record_type: RECORD_TYPE,
      generated_at: generatedAt || new Date().toISOString(),
      method: METHOD,
      method_version: VERSION,
      schema_version: SCHEMA_VERSION
    });
  }

  return {
    VERSION,
    RECORD_TYPE,
    METHOD,
    SCHEMA_VERSION,
    NarrativeRiskValidationError,
    normalizeInput,
    scoreNarrativeRisk,
    buildNarrativeRiskRecord
  };
});
