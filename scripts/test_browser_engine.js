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
    () => engine.buildNarrativeRiskRecord(testCase.payload, '2026-07-17T12:00:00.000Z'),
    error => error.name === 'NarrativeRiskValidationError' && error.message === testCase.message,
    testCase.name
  );
}
const zero = engine.scoreNarrativeRisk({
  claim: 'Zero weights remain zero.', source_type: 'official_or_primary', evidence_strength: 'strong',
  uncertainty: 'low', narrative_volatility: 'low', stakeholder_pressure: 'low', time_sensitivity: 'low',
  consequences: 'low', review_status: 'reviewed', source_count: 5
});
assert.strictEqual(zero.components.source_type, 0);
assert.strictEqual(zero.components.evidence_strength, 0);
assert.strictEqual(zero.components.review_status, 0);
console.log(`Browser engine contract passed: ${fixture.valid.length} valid and ${fixture.invalid.length} invalid fixtures.`);
