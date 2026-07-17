#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const engine = require(path.join(root, 'wordpress/catalyst-narrative-risk-demo/assets/narrative-risk-engine.js'));
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/scoring-parity.json'), 'utf8'));
const output = {
  version: engine.VERSION,
  valid: fixture.valid.map(testCase => ({ name: testCase.name, result: engine.scoreNarrativeRisk(testCase.payload) })),
  invalid: fixture.invalid.map(testCase => {
    try {
      engine.buildNarrativeRiskRecord(testCase.payload, '2026-07-17T12:00:00.000Z');
      return { name: testCase.name, message: null };
    } catch (error) {
      return { name: testCase.name, message: error.message };
    }
  })
};
process.stdout.write(JSON.stringify(output));
