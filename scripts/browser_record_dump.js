#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const engine = require(path.join(root, 'wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js'));
const payload = JSON.parse(fs.readFileSync(path.join(root, 'data/sample_narrative_risk_input.json'), 'utf8'));
const record = engine.buildNarrativeRiskRecord(payload, {
  generated_at: '2026-07-17T12:00:00+00:00',
  record_id: 'urn:uuid:10000000-0000-4000-8000-000000000001',
  case_id: 'urn:uuid:10000000-0000-4000-8000-000000000002',
  human_decision: {
    status: 'reviewed', disposition: 'approved_with_conditions', reviewer_id: 'reviewer-17',
    reviewer_name: 'Review Lead', reviewed_at: '2026-07-17T13:00:00+00:00',
    notes: 'Use within the measured pilot boundary.'
  }
});
process.stdout.write(JSON.stringify(record));
