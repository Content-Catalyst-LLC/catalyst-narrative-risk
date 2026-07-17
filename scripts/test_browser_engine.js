#!/usr/bin/env node
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const engine = require(path.join(root, 'wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js'));
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/scoring-parity.json'), 'utf8'));

assert.strictEqual(engine.VERSION, fixture.contract_version);
for (const testCase of fixture.valid) {
  assert.deepStrictEqual(engine.scoreNarrativeRisk(testCase.payload), testCase.expected, testCase.name);
}
for (const testCase of fixture.invalid) {
  assert.throws(
    () => engine.scoreNarrativeRisk(testCase.payload),
    error => error.name === 'NarrativeRiskValidationError' && error.message === testCase.message,
    testCase.name
  );
}
const zero = engine.scoreNarrativeRisk({
  claim: 'Zero weights remain zero.', source_type: 'official_or_primary', evidence_strength: 'strong',
  uncertainty: 'low', narrative_volatility: 'low', stakeholder_pressure: 'low', time_sensitivity: 'low',
  consequences: 'low', review_status: 'reviewed', source_count: 5
});
assert.strictEqual(zero.calculations.components.source_type.weight, 0);
assert.strictEqual(zero.calculations.components.evidence_strength.weight, 0);
assert.strictEqual(zero.calculations.components.review_status.weight, 0);
const record = engine.buildNarrativeRiskRecord({ claim: 'Browser reproducibility test.' }, {
  generated_at: '2026-07-17T12:00:00+00:00',
  record_id: 'urn:uuid:00000000-0000-4000-8000-000000000001',
  case_id: 'urn:uuid:00000000-0000-4000-8000-000000000002'
});
assert.deepStrictEqual(engine.verifyRecordReproducibility(record), {
  exact_match: true,
  method_snapshot_hash_match: true,
  canonical_input_hash_match: true,
  record_payload_hash_match: true,
  record_id: 'urn:uuid:00000000-0000-4000-8000-000000000001',
  method_id: engine.METHOD_ID,
  method_version: '1.1.0',
  schema_id: engine.SCHEMA_ID
});
console.log(`Browser engine contract passed: ${fixture.valid.length} valid and ${fixture.invalid.length} invalid fixtures.`);
