(function (root, factory) {
  'use strict';
  const method = typeof module === 'object' && module.exports
    ? require('./narrative-risk-method.js')
    : root.CatalystNarrativeRiskMethodV110;
  const engine = factory(method);
  if (typeof module === 'object' && module.exports) module.exports = engine;
  if (root) root.CatalystNarrativeRiskEngine = engine;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (DEFAULT_METHOD) {
  'use strict';

  const VERSION = '1.1.0';
  const RECORD_TYPE = 'catalyst_narrative_risk_record';
  const CONTRACT_ID = 'urn:catalyst:narrative-risk:contract:canonical';
  const METHOD_ID = 'urn:catalyst:narrative-risk:method:transparent-heuristic';
  const SCHEMA_ID = 'https://sustainablecatalyst.com/schemas/narrative-risk/record/1.1.0';
  const INPUT_SCHEMA_ID = 'https://sustainablecatalyst.com/schemas/narrative-risk/input/1.1.0';
  const INPUT_FIELDS = new Set([
    'claim', 'source_type', 'evidence_strength', 'uncertainty', 'narrative_volatility',
    'stakeholder_pressure', 'time_sensitivity', 'consequences', 'review_status',
    'source_count', 'method_notes'
  ]);
  const HUMAN_DECISION_FIELDS = new Set([
    'status', 'disposition', 'reviewer_id', 'reviewer_name', 'reviewed_at', 'notes'
  ]);
  const HUMAN_STATUS = ['draft', 'pending_review', 'reviewed'];
  const HUMAN_DISPOSITIONS = ['undecided', 'approved', 'approved_with_conditions', 'revise', 'rejected'];

  class NarrativeRiskValidationError extends Error {
    constructor(message) {
      super(message);
      this.name = 'NarrativeRiskValidationError';
    }
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function canonicalValue(value) {
    if (Array.isArray(value)) return value.map(canonicalValue);
    if (value && typeof value === 'object') {
      return Object.keys(value).sort().reduce(function (output, key) {
        output[key] = canonicalValue(value[key]);
        return output;
      }, {});
    }
    return value;
  }

  function canonicalJson(value) {
    return JSON.stringify(canonicalValue(value));
  }

  function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    const bitLength = bytes.length * 8;
    const totalLength = Math.ceil((bytes.length + 9) / 64) * 64;
    const padded = new Uint8Array(totalLength);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(totalLength - 8, Math.floor(bitLength / 0x100000000), false);
    view.setUint32(totalLength - 4, bitLength >>> 0, false);

    const K = [
      0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
      0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
      0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
      0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    ];
    const H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    const w = new Uint32Array(64);
    const rotr = function (value, amount) { return (value >>> amount) | (value << (32 - amount)); };

    for (let offset = 0; offset < totalLength; offset += 64) {
      for (let i = 0; i < 16; i += 1) w[i] = view.getUint32(offset + i * 4, false);
      for (let i = 16; i < 64; i += 1) {
        const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let a=H[0], b=H[1], c=H[2], d=H[3], e=H[4], f=H[5], g=H[6], h=H[7];
      for (let i = 0; i < 64; i += 1) {
        const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const ch = (e & f) ^ ((~e) & g);
        const temp1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
        const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const temp2 = (S0 + maj) >>> 0;
        h=g; g=f; f=e; e=(d + temp1) >>> 0; d=c; c=b; b=a; a=(temp1 + temp2) >>> 0;
      }
      H[0]=(H[0]+a)>>>0; H[1]=(H[1]+b)>>>0; H[2]=(H[2]+c)>>>0; H[3]=(H[3]+d)>>>0;
      H[4]=(H[4]+e)>>>0; H[5]=(H[5]+f)>>>0; H[6]=(H[6]+g)>>>0; H[7]=(H[7]+h)>>>0;
    }
    return H.map(function (value) { return value.toString(16).padStart(8, '0'); }).join('');
  }

  function digest(value) {
    return sha256(canonicalJson(value));
  }

  function validateMethod(method) {
    if (!method || typeof method !== 'object' || Array.isArray(method)) {
      throw new NarrativeRiskValidationError('method_snapshot must be a JSON object');
    }
    if (method.method_id !== METHOD_ID || method.method_version !== VERSION) {
      throw new NarrativeRiskValidationError('method_snapshot identifier or version is not supported by this release');
    }
    if (!method.algorithm || method.algorithm.type !== 'weighted_additive_v1' || method.algorithm.rounding !== 'half_up') {
      throw new NarrativeRiskValidationError('method_snapshot algorithm is not supported by this release');
    }
    return method;
  }

  function cleanText(value, field, required) {
    if (value === undefined || value === null) value = '';
    if (typeof value !== 'string') throw new NarrativeRiskValidationError(field + ' must be a string');
    const cleaned = value.trim();
    if (required && !cleaned) throw new NarrativeRiskValidationError(field + ' is required');
    return cleaned;
  }

  function cleanChoice(value, field, allowed, defaultValue) {
    if (value === undefined || value === null) return defaultValue;
    if (typeof value !== 'string') throw new NarrativeRiskValidationError(field + ' must be a string');
    const cleaned = value.trim().toLowerCase();
    if (!allowed.includes(cleaned)) {
      throw new NarrativeRiskValidationError(field + ' must be one of: ' + allowed.join(', '));
    }
    return cleaned;
  }

  function cleanSourceCount(value, defaultValue) {
    if (value === undefined || value === null || value === '') return defaultValue;
    if (typeof value === 'boolean') throw new NarrativeRiskValidationError('source_count must be a non-negative integer');
    const parsed = typeof value === 'number' ? value : (typeof value === 'string' && /^\d+$/.test(value.trim()) ? Number(value.trim()) : NaN);
    if (!Number.isInteger(parsed) || parsed < 0) throw new NarrativeRiskValidationError('source_count must be a non-negative integer');
    if (parsed > 1000000) throw new NarrativeRiskValidationError('source_count must be no greater than 1000000');
    return parsed;
  }

  function normalizeInput(payload, methodSnapshot) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new NarrativeRiskValidationError('payload must be a JSON object');
    }
    const unknown = Object.keys(payload).filter(function (key) { return !INPUT_FIELDS.has(key); }).sort();
    if (unknown.length) throw new NarrativeRiskValidationError('unsupported input field(s): ' + unknown.join(', '));
    const method = validateMethod(clone(methodSnapshot || DEFAULT_METHOD));
    const defaults = method.defaults;
    const weights = method.weights;
    return {
      claim: cleanText(payload.claim, 'claim', true),
      source_type: cleanChoice(payload.source_type, 'source_type', Object.keys(weights.source_type), defaults.source_type),
      evidence_strength: cleanChoice(payload.evidence_strength, 'evidence_strength', Object.keys(weights.evidence_strength), defaults.evidence_strength),
      uncertainty: cleanChoice(payload.uncertainty, 'uncertainty', Object.keys(weights.three_level_scale), defaults.uncertainty),
      narrative_volatility: cleanChoice(payload.narrative_volatility, 'narrative_volatility', Object.keys(weights.three_level_scale), defaults.narrative_volatility),
      stakeholder_pressure: cleanChoice(payload.stakeholder_pressure, 'stakeholder_pressure', Object.keys(weights.three_level_scale), defaults.stakeholder_pressure),
      time_sensitivity: cleanChoice(payload.time_sensitivity, 'time_sensitivity', Object.keys(weights.three_level_scale), defaults.time_sensitivity),
      consequences: cleanChoice(payload.consequences, 'consequences', Object.keys(weights.consequences), defaults.consequences),
      review_status: cleanChoice(payload.review_status, 'review_status', Object.keys(weights.review_status), defaults.review_status),
      source_count: cleanSourceCount(payload.source_count, defaults.source_count),
      method_notes: cleanText(payload.method_notes === undefined ? defaults.method_notes : payload.method_notes, 'method_notes', false)
    };
  }

  function sourceCountWeight(count, ranges) {
    for (const item of ranges) {
      if (count >= item.minimum && (item.maximum === null || count <= item.maximum)) return item.weight;
    }
    throw new NarrativeRiskValidationError('method_snapshot has no source-count range for the normalized input');
  }

  function evaluateRule(rule, normalized, score, current) {
    if (rule.operator === 'if_empty') return current.length === 0;
    if (rule.operator === 'if_empty_and_score_lt') return current.length === 0 && score < rule.value;
    if (rule.operator === 'any_eq') return (rule.fields || []).some(function (field) { return normalized[field] === rule.value; });
    const actual = normalized[rule.field];
    if (rule.operator === 'lte') return actual <= rule.value;
    if (rule.operator === 'eq') return actual === rule.value;
    if (rule.operator === 'neq') return actual !== rule.value;
    if (rule.operator === 'in') return rule.value.includes(actual);
    throw new NarrativeRiskValidationError('unsupported method rule operator: ' + rule.operator);
  }

  function applyRules(rules, normalized, score) {
    const output = [];
    rules.forEach(function (rule) {
      if (evaluateRule(rule, normalized, score, output)) output.push(rule.text);
    });
    return output;
  }

  function scoreNarrativeRisk(payload, methodSnapshot) {
    const method = validateMethod(clone(methodSnapshot || DEFAULT_METHOD));
    const normalized = normalizeInput(payload, method);
    const components = {};
    method.algorithm.component_order.forEach(function (key) {
      const metadata = method.components[key];
      const inputValue = normalized[metadata.input_field];
      const weight = metadata.weight_table === 'source_count_penalties'
        ? sourceCountWeight(inputValue, method.weights.source_count_penalties)
        : method.weights[metadata.weight_table][inputValue];
      components[key] = {
        input_value: inputValue,
        weight: weight,
        rationale: metadata.rationale,
        remediation: metadata.remediation
      };
    });
    const rawTotal = Object.values(components).reduce(function (sum, item) { return sum + item.weight; }, 0);
    const scaledScore = Number((rawTotal * method.algorithm.multiplier).toFixed(6));
    const riskScore = Math.max(method.algorithm.minimum_score, Math.min(method.algorithm.maximum_score, Math.floor(scaledScore + 0.5)));
    const threshold = clone(method.algorithm.thresholds.find(function (item) {
      return riskScore >= item.minimum && riskScore <= item.maximum;
    }));
    if (!threshold) throw new NarrativeRiskValidationError('method_snapshot thresholds do not cover the calculated score');
    const riskLevel = threshold.level;
    return {
      normalized_input: normalized,
      calculations: {
        components: components,
        raw_total: rawTotal,
        multiplier: method.algorithm.multiplier,
        scaled_score: scaledScore,
        risk_score: riskScore,
        threshold: threshold
      },
      interpretation: {
        risk_level: riskLevel,
        flags: applyRules(method.interpretation.flag_rules, normalized, riskScore),
        review_actions: applyRules(method.interpretation.action_rules, normalized, riskScore),
        decision_note: method.interpretation.decision_notes[riskLevel]
      }
    };
  }

  function validateDateTime(value, field) {
    if (typeof value !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) || Number.isNaN(Date.parse(value))) {
      throw new NarrativeRiskValidationError(field + ' must be an ISO 8601 date-time string');
    }
    return value;
  }

  function randomUuid() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') return globalThis.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (character) {
      const random = Math.floor(Math.random() * 16);
      const value = character === 'x' ? random : ((random & 0x3) | 0x8);
      return value.toString(16);
    });
  }

  function urnUuid(value, field) {
    const candidate = value || ('urn:uuid:' + randomUuid());
    if (typeof candidate !== 'string' || !/^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(candidate)) {
      throw new NarrativeRiskValidationError(field + ' must be a urn:uuid identifier');
    }
    return candidate.toLowerCase();
  }

  function normalizeHumanDecision(payload) {
    const source = payload === undefined || payload === null ? {} : payload;
    if (!source || typeof source !== 'object' || Array.isArray(source)) throw new NarrativeRiskValidationError('human_decision must be a JSON object');
    const unknown = Object.keys(source).filter(function (key) { return !HUMAN_DECISION_FIELDS.has(key); }).sort();
    if (unknown.length) throw new NarrativeRiskValidationError('unsupported human_decision field(s): ' + unknown.join(', '));
    const reviewerId = source.reviewer_id === undefined ? null : source.reviewer_id;
    const reviewerName = source.reviewer_name === undefined ? null : source.reviewer_name;
    if (reviewerId !== null && typeof reviewerId !== 'string') throw new NarrativeRiskValidationError('human_decision.reviewer_id must be a string or null');
    if (reviewerName !== null && typeof reviewerName !== 'string') throw new NarrativeRiskValidationError('human_decision.reviewer_name must be a string or null');
    const reviewedAt = source.reviewed_at === undefined ? null : source.reviewed_at;
    if (reviewedAt !== null) validateDateTime(reviewedAt, 'human_decision.reviewed_at');
    return {
      status: cleanChoice(source.status, 'human_decision.status', HUMAN_STATUS, 'draft'),
      disposition: cleanChoice(source.disposition, 'human_decision.disposition', HUMAN_DISPOSITIONS, 'undecided'),
      reviewer_id: reviewerId,
      reviewer_name: reviewerName,
      reviewed_at: reviewedAt,
      notes: cleanText(source.notes === undefined ? '' : source.notes, 'human_decision.notes', false)
    };
  }

  function buildNarrativeRiskRecord(payload, options) {
    const opts = options || {};
    const method = validateMethod(clone(opts.method_snapshot || DEFAULT_METHOD));
    const analysis = scoreNarrativeRisk(payload, method);
    const generatedAt = opts.generated_at ? validateDateTime(opts.generated_at, 'generated_at') : new Date().toISOString();
    const record = {
      record_type: RECORD_TYPE,
      contract: { contract_id: CONTRACT_ID, contract_version: VERSION },
      identifiers: {
        record_id: urnUuid(opts.record_id, 'record_id'),
        case_id: urnUuid(opts.case_id, 'case_id'),
        method_id: METHOD_ID,
        schema_id: SCHEMA_ID,
        input_schema_id: INPUT_SCHEMA_ID
      },
      generated_at: generatedAt,
      normalized_input: analysis.normalized_input,
      method_snapshot: method,
      method_snapshot_sha256: digest(method),
      calculations: analysis.calculations,
      interpretation: analysis.interpretation,
      human_decision: normalizeHumanDecision(opts.human_decision)
    };
    if (opts.migration !== undefined && opts.migration !== null) record.migration = clone(opts.migration);
    record.reproducibility = {
      canonical_input_sha256: digest(record.normalized_input),
      record_payload_sha256: digest(record)
    };
    return record;
  }

  function reproduceNarrativeRiskRecord(record) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) throw new NarrativeRiskValidationError('record must be a JSON object');
    if (digest(record.method_snapshot) !== record.method_snapshot_sha256) {
      throw new NarrativeRiskValidationError('method_snapshot_sha256 does not match the embedded method snapshot');
    }
    return buildNarrativeRiskRecord(record.normalized_input, {
      generated_at: record.generated_at,
      record_id: record.identifiers.record_id,
      case_id: record.identifiers.case_id,
      human_decision: record.human_decision,
      method_snapshot: record.method_snapshot,
      migration: record.migration
    });
  }

  function verifyRecordReproducibility(record) {
    const payload = clone(record);
    const reproducibility = payload.reproducibility;
    delete payload.reproducibility;
    const reproduced = reproduceNarrativeRiskRecord(record);
    return {
      exact_match: canonicalJson(reproduced) === canonicalJson(record),
      method_snapshot_hash_match: digest(record.method_snapshot) === record.method_snapshot_sha256,
      canonical_input_hash_match: digest(record.normalized_input) === reproducibility.canonical_input_sha256,
      record_payload_hash_match: digest(payload) === reproducibility.record_payload_sha256,
      record_id: record.identifiers.record_id,
      method_id: record.identifiers.method_id,
      method_version: record.method_snapshot.method_version,
      schema_id: record.identifiers.schema_id
    };
  }

  return {
    VERSION: VERSION,
    RECORD_TYPE: RECORD_TYPE,
    CONTRACT_ID: CONTRACT_ID,
    METHOD_ID: METHOD_ID,
    SCHEMA_ID: SCHEMA_ID,
    INPUT_SCHEMA_ID: INPUT_SCHEMA_ID,
    METHOD_SNAPSHOT: clone(DEFAULT_METHOD),
    NarrativeRiskValidationError: NarrativeRiskValidationError,
    canonicalJson: canonicalJson,
    sha256: sha256,
    digest: digest,
    normalizeInput: normalizeInput,
    normalizeHumanDecision: normalizeHumanDecision,
    scoreNarrativeRisk: scoreNarrativeRisk,
    buildNarrativeRiskRecord: buildNarrativeRiskRecord,
    reproduceNarrativeRiskRecord: reproduceNarrativeRiskRecord,
    verifyRecordReproducibility: verifyRecordReproducibility
  };
});
