#!/usr/bin/env node
'use strict';
const path = require('path');
const root = path.resolve(__dirname, '..');
const engine = require(path.join(root, 'wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js'));
const record = engine.buildNarrativeRiskRecord({
  claim: 'A Montréal climate narrative requires transparent review.',
  source_type: 'official_or_primary',
  evidence_strength: 'strong',
  uncertainty: 'low',
  narrative_volatility: 'medium',
  stakeholder_pressure: 'low',
  time_sensitivity: 'high',
  consequences: 'high',
  review_status: 'reviewed',
  source_count: 5,
  method_notes: 'Unicode and digest parity fixture.'
}, {
  generated_at: '2026-07-17T12:00:00+00:00',
  record_id: 'urn:uuid:10000000-0000-4000-8000-000000000001',
  case_id: 'urn:uuid:10000000-0000-4000-8000-000000000002',
  human_decision: {
    status: 'reviewed', disposition: 'approved_with_conditions', reviewer_id: 'reviewer-17',
    reviewer_name: 'Review Lead', reviewed_at: '2026-07-17T13:00:00+00:00', notes: 'Use with the stated time boundary.'
  }
});
process.stdout.write(JSON.stringify(record));
