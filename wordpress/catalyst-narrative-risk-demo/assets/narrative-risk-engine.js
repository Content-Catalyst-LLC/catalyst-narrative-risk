(function (root, factory) {
  'use strict';
  const method = typeof module === 'object' && module.exports
    ? require('./narrative-risk-method.js')
    : root.CatalystNarrativeRiskMethodV150;
  const narrativeMap = typeof module === 'object' && module.exports
    ? require('./narrative-risk-map.js')
    : root.CatalystNarrativeRiskMap;
  const engine = factory(method, narrativeMap);
  if (typeof module === 'object' && module.exports) module.exports = engine;
  if (root) root.CatalystNarrativeRiskEngine = engine;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (DEFAULT_METHOD, NARRATIVE_MAP) {
  'use strict';

  const VERSION = '1.6.0';
  const RECORD_TYPE = 'catalyst_narrative_risk_record';
  const CONTRACT_ID = 'urn:catalyst:narrative-risk:contract:canonical';
  const METHOD_ID = 'urn:catalyst:narrative-risk:method:transparent-heuristic';
  const SCHEMA_ID = 'https://sustainablecatalyst.com/schemas/narrative-risk/record/1.6.0';
  const INPUT_SCHEMA_ID = 'https://sustainablecatalyst.com/schemas/narrative-risk/input/1.6.0';
  const LEDGER_SCHEMA_ID = 'https://sustainablecatalyst.com/schemas/narrative-risk/evidence-ledger/1.6.0';
  const NARRATIVE_MAP_SCHEMA_ID = 'https://sustainablecatalyst.com/schemas/narrative-risk/narrative-map/1.6.0';
  const INPUT_FIELDS = new Set([
    'claim', 'source_type', 'evidence_strength', 'uncertainty', 'narrative_volatility',
    'stakeholder_pressure', 'time_sensitivity', 'consequences', 'review_status', 'source_count',
    'method_notes', 'claims', 'sources', 'evidence_items', 'relationships',
    'narrative_nodes', 'narrative_links', 'wording_variants', 'selected_variant_id'
  ]);
  const HUMAN_DECISION_FIELDS = new Set(['status', 'disposition', 'reviewer_id', 'reviewer_name', 'reviewed_at', 'notes']);
  const HUMAN_STATUS = ['draft', 'pending_review', 'reviewed'];
  const HUMAN_DISPOSITIONS = ['undecided', 'approved', 'approved_with_conditions', 'revise', 'rejected'];
  const CLAIM_TYPES = ['factual', 'causal', 'predictive', 'normative', 'recommendation', 'interpretive'];
  const CLAIM_ROLES = ['primary', 'supporting', 'context'];
  const EVIDENCE_TYPES = ['quote', 'data', 'finding', 'observation', 'method', 'context'];
  const RELATION_TYPES = ['support', 'qualify', 'contradict', 'contextualize', 'unresolved'];
  const DIRECTNESS_VALUES = ['direct', 'indirect', 'mixed', 'unknown'];
  const FRESHNESS_VALUES = ['current', 'aging', 'stale', 'unknown'];
  const ACQUISITION_METHODS = ['manual', 'knowledge_library', 'catalyst_data', 'api', 'document_import', 'other'];
  const IDENTIFIER_SCHEMES = ['doi', 'isbn', 'issn', 'url', 'handle', 'ark', 'catalog', 'other'];
  const STRENGTH_VALUES = ['strong', 'moderate', 'limited', 'weak', 'unclear'];
  const SOURCE_TYPES = ['official_or_primary', 'peer_reviewed_or_audited', 'reputable_secondary', 'internal_unreviewed', 'single_report_or_media', 'social_or_anecdotal', 'unknown'];
  const LEDGER_ID_RE = /^urn:catalyst:narrative-risk:(claim|source|evidence|relationship):sha256:[0-9a-f]{64}$/;
  const HEX64_RE = /^[0-9a-f]{64}$/;

  class NarrativeRiskValidationError extends Error {
    constructor(message) {
      super(message);
      this.name = 'NarrativeRiskValidationError';
    }
  }

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
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
  function canonicalJson(value) { return JSON.stringify(canonicalValue(value)); }

  function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    const bitLength = bytes.length * 8;
    const totalLength = Math.ceil((bytes.length + 9) / 64) * 64;
    const padded = new Uint8Array(totalLength);
    padded.set(bytes); padded[bytes.length] = 0x80;
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
  function digest(value) { return sha256(canonicalJson(value)); }

  function validateMethod(method) {
    if (!method || typeof method !== 'object' || Array.isArray(method)) throw new NarrativeRiskValidationError('method_snapshot must be a JSON object');
    if (method.method_id !== METHOD_ID || method.method_version !== VERSION) throw new NarrativeRiskValidationError('method_snapshot identifier or version is not supported by this release');
    if (!method.algorithm || method.algorithm.type !== 'weighted_additive_v1' || method.algorithm.rounding !== 'half_up' || !method.ledger_policy || !method.narrative_map_policy) {
      throw new NarrativeRiskValidationError('method_snapshot algorithm is not supported by this release');
    }
    return method;
  }
  function cleanText(value, field, required, maximum) {
    if (value === undefined || value === null) value = '';
    if (typeof value !== 'string') throw new NarrativeRiskValidationError(field + ' must be a string');
    const cleaned = value.trim();
    if (required && !cleaned) throw new NarrativeRiskValidationError(field + ' is required');
    if (maximum !== undefined && cleaned.length > maximum) throw new NarrativeRiskValidationError(field + ' must be no longer than ' + maximum + ' characters');
    return cleaned;
  }
  function cleanChoice(value, field, allowed, defaultValue) {
    if (value === undefined || value === null) return defaultValue;
    if (typeof value !== 'string') throw new NarrativeRiskValidationError(field + ' must be a string');
    const cleaned = value.trim().toLowerCase();
    if (!allowed.includes(cleaned)) throw new NarrativeRiskValidationError(field + ' must be one of: ' + allowed.join(', '));
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
  function nullableText(value, field, maximum) {
    if (value === undefined || value === null || value === '') return null;
    return cleanText(value, field, true, maximum || 5000);
  }
  function validateDateTime(value, field) {
    if (typeof value !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) || Number.isNaN(Date.parse(value))) {
      throw new NarrativeRiskValidationError(field + ' must be an ISO 8601 date-time string');
    }
    return value;
  }
  function dateTimeOrNull(value, field) {
    if (value === undefined || value === null || value === '') return null;
    try { return validateDateTime(value, field); }
    catch (_error) { throw new NarrativeRiskValidationError(field + ' must be an ISO 8601 date-time string or null'); }
  }
  function urlOrNull(value, field) {
    const cleaned = nullableText(value, field, 5000);
    if (cleaned === null) return null;
    try {
      const parsed = new URL(cleaned);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('protocol');
    } catch (_error) { throw new NarrativeRiskValidationError(field + ' must be an absolute http or https URL'); }
    return cleaned;
  }
  function yearOrNull(value, field) {
    if (value === undefined || value === null || value === '') return null;
    if (!Number.isInteger(value)) throw new NarrativeRiskValidationError(field + ' must be an integer or null');
    if (value < -10000 || value > 9999) throw new NarrativeRiskValidationError(field + ' must be between -10000 and 9999');
    return value;
  }
  function asArray(value, field) {
    if (value === undefined || value === null) return [];
    if (!Array.isArray(value)) throw new NarrativeRiskValidationError(field + ' must be an array');
    return value;
  }
  function asObject(value, field, allowed) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new NarrativeRiskValidationError(field + ' must be a JSON object');
    const unknown = Object.keys(value).filter(function (key) { return !allowed.has(key); }).sort();
    if (unknown.length) throw new NarrativeRiskValidationError('unsupported ' + field + ' field(s): ' + unknown.join(', '));
    return value;
  }
  function stableLedgerId(kind, material) {
    if (!['claim','source','evidence','relationship'].includes(kind)) throw new NarrativeRiskValidationError('unsupported ledger identifier kind: ' + kind);
    return 'urn:catalyst:narrative-risk:' + kind + ':sha256:' + digest(material);
  }
  function ledgerId(value, kind, material, field) {
    if (value === undefined || value === null || value === '') return stableLedgerId(kind, material);
    if (typeof value !== 'string' || !LEDGER_ID_RE.test(value) || !value.includes(':' + kind + ':')) {
      throw new NarrativeRiskValidationError(field + ' must be a canonical ' + kind + ' identifier');
    }
    return value;
  }
  function ensureUnique(items, key, field) {
    const seen = new Set();
    for (const item of items) {
      if (seen.has(item[key])) throw new NarrativeRiskValidationError('duplicate ' + field + ': ' + item[key]);
      seen.add(item[key]);
    }
  }

  function normalizeClaims(raw, narrativeClaim) {
    let values = asArray(raw, 'claims');
    if (!values.length) values = [{ text: narrativeClaim, claim_type: 'factual', role: 'primary', notes: '' }];
    const allowed = new Set(['claim_id','text','claim_type','role','notes']);
    const claims = values.map(function (rawClaim, index) {
      const item = asObject(rawClaim, 'claims[' + index + ']', allowed);
      const text = cleanText(item.text, 'claims[' + index + '].text', true, 20000);
      const claimType = cleanChoice(item.claim_type, 'claims[' + index + '].claim_type', CLAIM_TYPES, 'factual');
      const role = cleanChoice(item.role, 'claims[' + index + '].role', CLAIM_ROLES, index === 0 ? 'primary' : 'supporting');
      const notes = cleanText(item.notes === undefined ? '' : item.notes, 'claims[' + index + '].notes', false, 50000);
      const material = { index: index, text: text, claim_type: claimType, role: role };
      return { claim_id: ledgerId(item.claim_id, 'claim', material, 'claims[' + index + '].claim_id'), text: text, claim_type: claimType, role: role, notes: notes };
    });
    ensureUnique(claims, 'claim_id', 'claim_id');
    const primary = claims.filter(function (item) { return item.role === 'primary'; });
    if (primary.length !== 1) throw new NarrativeRiskValidationError('claims must contain exactly one primary claim');
    if (primary[0].text !== narrativeClaim) throw new NarrativeRiskValidationError('claim must exactly match the primary claim text');
    return claims;
  }
  function compareText(a, b) { return a < b ? -1 : (a > b ? 1 : 0); }
  function normalizeIdentifiers(raw, field) {
    const allowed = new Set(['scheme','value']);
    const output = asArray(raw, field).map(function (rawIdentifier, index) {
      const item = asObject(rawIdentifier, field + '[' + index + ']', allowed);
      return { scheme: cleanChoice(item.scheme, field + '[' + index + '].scheme', IDENTIFIER_SCHEMES, 'other'), value: cleanText(item.value, field + '[' + index + '].value', true, 5000) };
    });
    output.sort(function (a, b) { return compareText(a.scheme, b.scheme) || compareText(a.value, b.value); });
    const seen = new Set();
    output.forEach(function (item) {
      const key = item.scheme + '\u0000' + item.value;
      if (seen.has(key)) throw new NarrativeRiskValidationError(field + ' contains duplicate identifiers');
      seen.add(key);
    });
    return output;
  }
  function normalizeProvenance(raw, field) {
    const item = asObject(raw === undefined || raw === null ? {} : raw, field, new Set(['acquisition_method','imported_from','imported_at','content_sha256']));
    let contentHash = item.content_sha256;
    if (contentHash === undefined || contentHash === null || contentHash === '') contentHash = null;
    else if (typeof contentHash !== 'string' || !HEX64_RE.test(contentHash)) throw new NarrativeRiskValidationError(field + '.content_sha256 must be a lowercase SHA-256 digest or null');
    return {
      acquisition_method: cleanChoice(item.acquisition_method, field + '.acquisition_method', ACQUISITION_METHODS, 'manual'),
      imported_from: nullableText(item.imported_from, field + '.imported_from', 5000),
      imported_at: dateTimeOrNull(item.imported_at, field + '.imported_at'),
      content_sha256: contentHash
    };
  }
  function normalizeSources(raw) {
    const allowed = new Set(['source_id','title','source_type','creators','publisher','published_year','url','accessed_at','identifiers','independence_group','duplicate_of_source_id','directness','freshness','provenance','notes']);
    const sources = asArray(raw, 'sources').map(function (rawSource, index) {
      const item = asObject(rawSource, 'sources[' + index + ']', allowed);
      const creators = asArray(item.creators, 'sources[' + index + '].creators').map(function (value) { return cleanText(value, 'sources[' + index + '].creators', true, 1000); });
      const identifiers = normalizeIdentifiers(item.identifiers, 'sources[' + index + '].identifiers');
      const title = cleanText(item.title, 'sources[' + index + '].title', true, 20000);
      const sourceType = cleanChoice(item.source_type, 'sources[' + index + '].source_type', SOURCE_TYPES, 'unknown');
      const publisher = cleanText(item.publisher === undefined ? '' : item.publisher, 'sources[' + index + '].publisher', false, 5000);
      const publishedYear = yearOrNull(item.published_year, 'sources[' + index + '].published_year');
      const url = urlOrNull(item.url, 'sources[' + index + '].url');
      const accessedAt = dateTimeOrNull(item.accessed_at, 'sources[' + index + '].accessed_at');
      const directness = cleanChoice(item.directness, 'sources[' + index + '].directness', DIRECTNESS_VALUES, 'unknown');
      const freshness = cleanChoice(item.freshness, 'sources[' + index + '].freshness', FRESHNESS_VALUES, 'unknown');
      const provenance = normalizeProvenance(item.provenance, 'sources[' + index + '].provenance');
      const notes = cleanText(item.notes === undefined ? '' : item.notes, 'sources[' + index + '].notes', false, 50000);
      const material = { index: index, title: title, source_type: sourceType, creators: creators, publisher: publisher, published_year: publishedYear, url: url, identifiers: identifiers };
      const sourceId = ledgerId(item.source_id, 'source', material, 'sources[' + index + '].source_id');
      let duplicate = item.duplicate_of_source_id;
      if (duplicate === undefined || duplicate === null || duplicate === '') duplicate = null;
      else if (typeof duplicate !== 'string' || !LEDGER_ID_RE.test(duplicate) || !duplicate.includes(':source:')) throw new NarrativeRiskValidationError('sources[' + index + '].duplicate_of_source_id must be a canonical source identifier or null');
      const independenceGroup = nullableText(item.independence_group, 'sources[' + index + '].independence_group', 1000);
      return { source_id: sourceId, title: title, source_type: sourceType, creators: creators, publisher: publisher, published_year: publishedYear, url: url, accessed_at: accessedAt, identifiers: identifiers, independence_group: independenceGroup || sourceId, duplicate_of_source_id: duplicate, directness: directness, freshness: freshness, provenance: provenance, notes: notes };
    });
    ensureUnique(sources, 'source_id', 'source_id');
    const byId = Object.fromEntries(sources.map(function (item) { return [item.source_id, item]; }));
    sources.forEach(function (item) {
      const duplicate = item.duplicate_of_source_id;
      if (duplicate === null) return;
      if (duplicate === item.source_id) throw new NarrativeRiskValidationError('a source cannot duplicate itself');
      if (!byId[duplicate]) throw new NarrativeRiskValidationError('duplicate source reference does not exist: ' + duplicate);
      if (item.independence_group === item.source_id) item.independence_group = byId[duplicate].independence_group;
    });
    return sources;
  }
  function normalizeEvidence(raw, sourceIds) {
    const allowed = new Set(['evidence_id','source_id','evidence_type','excerpt','locator','captured_at','notes']);
    const output = asArray(raw, 'evidence_items').map(function (rawEvidence, index) {
      const item = asObject(rawEvidence, 'evidence_items[' + index + ']', allowed);
      const sourceId = item.source_id;
      if (typeof sourceId !== 'string' || !sourceIds.has(sourceId)) throw new NarrativeRiskValidationError('evidence_items[' + index + '].source_id does not reference a normalized source');
      const evidenceType = cleanChoice(item.evidence_type, 'evidence_items[' + index + '].evidence_type', EVIDENCE_TYPES, 'finding');
      const excerpt = cleanText(item.excerpt, 'evidence_items[' + index + '].excerpt', true, 200000);
      const locator = cleanText(item.locator === undefined ? '' : item.locator, 'evidence_items[' + index + '].locator', false, 5000);
      const capturedAt = dateTimeOrNull(item.captured_at, 'evidence_items[' + index + '].captured_at');
      const notes = cleanText(item.notes === undefined ? '' : item.notes, 'evidence_items[' + index + '].notes', false, 50000);
      const excerptHash = digest(excerpt);
      const material = { index: index, source_id: sourceId, evidence_type: evidenceType, excerpt_sha256: excerptHash, locator: locator };
      return { evidence_id: ledgerId(item.evidence_id, 'evidence', material, 'evidence_items[' + index + '].evidence_id'), source_id: sourceId, evidence_type: evidenceType, excerpt: excerpt, locator: locator, captured_at: capturedAt, excerpt_sha256: excerptHash, notes: notes };
    });
    ensureUnique(output, 'evidence_id', 'evidence_id');
    return output;
  }
  function normalizeRelationships(raw, claimIds, evidenceIds) {
    const allowed = new Set(['relationship_id','claim_id','evidence_id','relation_type','strength','notes']);
    const output = asArray(raw, 'relationships').map(function (rawRelationship, index) {
      const item = asObject(rawRelationship, 'relationships[' + index + ']', allowed);
      if (typeof item.claim_id !== 'string' || !claimIds.has(item.claim_id)) throw new NarrativeRiskValidationError('relationships[' + index + '].claim_id does not reference a normalized claim');
      if (typeof item.evidence_id !== 'string' || !evidenceIds.has(item.evidence_id)) throw new NarrativeRiskValidationError('relationships[' + index + '].evidence_id does not reference normalized evidence');
      const relationType = cleanChoice(item.relation_type, 'relationships[' + index + '].relation_type', RELATION_TYPES, 'unresolved');
      const strength = cleanChoice(item.strength, 'relationships[' + index + '].strength', STRENGTH_VALUES, 'unclear');
      const notes = cleanText(item.notes === undefined ? '' : item.notes, 'relationships[' + index + '].notes', false, 50000);
      const material = { index: index, claim_id: item.claim_id, evidence_id: item.evidence_id, relation_type: relationType, strength: strength };
      return { relationship_id: ledgerId(item.relationship_id, 'relationship', material, 'relationships[' + index + '].relationship_id'), claim_id: item.claim_id, evidence_id: item.evidence_id, relation_type: relationType, strength: strength, notes: notes };
    });
    ensureUnique(output, 'relationship_id', 'relationship_id');
    const seen = new Set();
    output.forEach(function (item) {
      const key = [item.claim_id,item.evidence_id,item.relation_type,item.strength].join('\u0000');
      if (seen.has(key)) throw new NarrativeRiskValidationError('duplicate claim-evidence relationship');
      seen.add(key);
    });
    return output;
  }
  function citationAuthor(creators) {
    if (!creators.length) return 'Unknown author';
    if (creators.length === 1) return creators[0];
    if (creators.length === 2) return creators[0] + ' and ' + creators[1];
    return creators[0] + ' et al.';
  }
  function harvardCitation(source) {
    const author = citationAuthor(source.creators);
    const year = source.published_year === null ? 'n.d.' : String(source.published_year);
    let text = author + ' (' + year + ') ' + source.title + '.';
    if (source.publisher) text += ' ' + source.publisher + '.';
    if (source.url) {
      text += ' Available at: ' + source.url;
      if (source.accessed_at) text += ' (Accessed: ' + source.accessed_at.slice(0, 10) + ')';
      text += '.';
    }
    return text;
  }
  function citationKey(source) {
    let token = source.creators.length ? source.creators[0].split(/\s+/).slice(-1)[0] : 'Unknown';
    token = token.replace(/[^A-Za-z0-9]+/g, '') || 'Source';
    const year = source.published_year === null ? 'nd' : source.published_year;
    return token + year + '-' + source.source_id.slice(-8);
  }
  function strengthRank(value, order) { return order.indexOf(value); }
  function downgrade(value, steps, order) { return order[Math.max(0, strengthRank(value, order) - steps)]; }
  function claimCoverage(claimId, relationships, evidenceById, sourceById, method) {
    const related = relationships.filter(function (item) { return item.claim_id === claimId; });
    const counts = { support:0, qualify:0, contradict:0, contextualize:0, unresolved:0 };
    related.forEach(function (item) { counts[item.relation_type] += 1; });
    const evidenceIds = new Set(related.map(function (item) { return item.evidence_id; }));
    const sourceIds = new Set(Array.from(evidenceIds).map(function (id) { return evidenceById[id].source_id; }));
    const groups = new Set(Array.from(sourceIds).map(function (id) { return sourceById[id].independence_group; }));
    const positiveTypes = new Set(method.ledger_policy.positive_relation_types);
    const positive = related.filter(function (item) { return positiveTypes.has(item.relation_type); });
    const order = method.ledger_policy.strength_order;
    let positiveStrength = 'unclear';
    positive.forEach(function (item) { if (strengthRank(item.strength, order) > strengthRank(positiveStrength, order)) positiveStrength = item.strength; });
    const contested = counts.contradict > 0;
    let status;
    if (contested) status = 'contested';
    else if (!positive.length) status = 'none';
    else {
      const positiveSourceIds = new Set(positive.map(function (item) { return evidenceById[item.evidence_id].source_id; }));
      const positiveGroups = new Set(Array.from(positiveSourceIds).map(function (id) { return sourceById[id].independence_group; }));
      const policy = method.ledger_policy;
      status = positiveGroups.size >= policy.substantial_minimum_independent_groups && strengthRank(positiveStrength, order) >= strengthRank(policy.substantial_minimum_strength, order) ? 'substantial' : 'partial';
    }
    return { claim_id: claimId, evidence_count: evidenceIds.size, source_count: sourceIds.size, independent_source_count: groups.size, relationship_counts: counts, positive_strength: positiveStrength, coverage_status: status, contested: contested };
  }
  function deriveScoringInputs(primaryClaimId, relationships, evidenceById, sourceById, method, fallback) {
    const primary = relationships.filter(function (item) { return item.claim_id === primaryClaimId; });
    if (!primary.length) return { ledger_applied:false, source_type:fallback.source_type, evidence_strength:fallback.evidence_strength, source_count:fallback.source_count, basis:'No primary-claim relationships were recorded; explicit or default scalar scoring inputs were retained.' };
    const sourceIds = new Set(primary.map(function (item) { return evidenceById[item.evidence_id].source_id; }));
    const positiveTypes = new Set(method.ledger_policy.positive_relation_types);
    const positive = primary.filter(function (item) { return positiveTypes.has(item.relation_type); });
    const positiveSourceIds = new Set(positive.map(function (item) { return evidenceById[item.evidence_id].source_id; }));
    const candidates = positiveSourceIds.size ? positiveSourceIds : sourceIds;
    let sourceType = 'unknown';
    Array.from(candidates).forEach(function (id) {
      const candidate = sourceById[id].source_type;
      if (sourceType === 'unknown' || method.weights.source_type[candidate] < method.weights.source_type[sourceType] || (method.weights.source_type[candidate] === method.weights.source_type[sourceType] && compareText(candidate, sourceType) < 0)) sourceType = candidate;
    });
    const order = method.ledger_policy.strength_order;
    let strength = 'unclear';
    positive.forEach(function (item) { if (strengthRank(item.strength, order) > strengthRank(strength, order)) strength = item.strength; });
    const groups = new Set(Array.from(positiveSourceIds).map(function (id) { return sourceById[id].independence_group; }));
    const policy = method.ledger_policy;
    if (positive.length && groups.size < policy.minimum_independent_groups_for_no_downgrade) strength = downgrade(strength, policy.single_group_downgrade_steps, order);
    if (primary.some(function (item) { return item.relation_type === 'contradict'; })) strength = downgrade(strength, policy.contradiction_downgrade_steps, order);
    return { ledger_applied:true, source_type:sourceType, evidence_strength:strength, source_count:sourceIds.size, basis:'Derived from evidence relationships linked to the primary claim using the embedded v1.6.0 ledger policy.' };
  }
  function buildEvidenceLedger(payload, narrativeClaim, method, fallback) {
    const claims = normalizeClaims(payload.claims, narrativeClaim);
    const sources = normalizeSources(payload.sources);
    const evidence = normalizeEvidence(payload.evidence_items, new Set(sources.map(function (item) { return item.source_id; })));
    const relationships = normalizeRelationships(payload.relationships, new Set(claims.map(function (item) { return item.claim_id; })), new Set(evidence.map(function (item) { return item.evidence_id; })));
    const primaryClaimId = claims.find(function (item) { return item.role === 'primary'; }).claim_id;
    const sourceById = Object.fromEntries(sources.map(function (item) { return [item.source_id, item]; }));
    const evidenceById = Object.fromEntries(evidence.map(function (item) { return [item.evidence_id, item]; }));
    const perClaim = claims.map(function (item) { return claimCoverage(item.claim_id, relationships, evidenceById, sourceById, method); });
    let overallStatus;
    if (perClaim.some(function (item) { return item.coverage_status === 'contested'; })) overallStatus = 'contested';
    else if (perClaim.every(function (item) { return item.coverage_status === 'substantial'; })) overallStatus = 'substantial';
    else if (perClaim.every(function (item) { return item.coverage_status === 'none'; })) overallStatus = 'none';
    else overallStatus = 'partial';
    return {
      ledger_version: VERSION,
      primary_claim_id: primaryClaimId,
      claims: claims,
      sources: sources,
      evidence_items: evidence,
      relationships: relationships,
      coverage: {
        per_claim: perClaim,
        overall: {
          claim_count: claims.length, source_count: sources.length, evidence_count: evidence.length, relationship_count: relationships.length,
          independent_source_count: new Set(sources.map(function (item) { return item.independence_group; })).size,
          duplicate_source_count: sources.filter(function (item) { return item.duplicate_of_source_id !== null; }).length,
          direct_source_count: sources.filter(function (item) { return item.directness === 'direct'; }).length,
          stale_source_count: sources.filter(function (item) { return item.freshness === 'stale'; }).length,
          unsupported_claim_count: perClaim.filter(function (item) { return item.relationship_counts.support + item.relationship_counts.qualify === 0; }).length,
          contested_claim_count: perClaim.filter(function (item) { return item.contested; }).length,
          coverage_status: overallStatus
        }
      },
      source_list: sources.map(function (item) { return { source_id:item.source_id, citation_key:citationKey(item), citation:harvardCitation(item) }; }),
      derived_scoring_inputs: deriveScoringInputs(primaryClaimId, relationships, evidenceById, sourceById, method, fallback)
    };
  }
  function ledgerInterpretation(ledger, method) {
    const primary = ledger.coverage.per_claim.find(function (item) { return item.claim_id === ledger.primary_claim_id; });
    const overall = ledger.coverage.overall;
    const evidenceById = Object.fromEntries(ledger.evidence_items.map(function (item) { return [item.evidence_id, item]; }));
    const primarySourceIds = new Set(ledger.relationships.filter(function (item) { return item.claim_id === ledger.primary_claim_id; }).map(function (item) { return evidenceById[item.evidence_id].source_id; }));
    const primarySources = ledger.sources.filter(function (item) { return primarySourceIds.has(item.source_id); });
    const texts = method.ledger_interpretation;
    const flags = [], actions = [];
    const relationTotal = Object.values(primary.relationship_counts).reduce(function (sum, value) { return sum + value; }, 0);
    if (!relationTotal) { flags.push(texts.flags.no_relationships); actions.push(texts.actions.record_relationships); }
    if (primary.contested) { flags.push(texts.flags.contested); actions.push(texts.actions.resolve_contestation); }
    if (overall.duplicate_source_count > 0 || primary.source_count > primary.independent_source_count) { flags.push(texts.flags.dependent_sources); actions.push(texts.actions.add_independent_sources); }
    if (primarySources.some(function (item) { return item.freshness === 'stale'; })) { flags.push(texts.flags.stale_sources); actions.push(texts.actions.refresh_stale_sources); }
    if (primarySources.length && primarySources.every(function (item) { return item.directness === 'indirect' || item.directness === 'unknown'; })) { flags.push(texts.flags.indirect_only); actions.push(texts.actions.add_direct_evidence); }
    return { flags:flags, actions:actions };
  }

  function normalizePayload(payload, methodSnapshot) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new NarrativeRiskValidationError('payload must be a JSON object');
    const unknown = Object.keys(payload).filter(function (key) { return !INPUT_FIELDS.has(key); }).sort();
    if (unknown.length) throw new NarrativeRiskValidationError('unsupported input field(s): ' + unknown.join(', '));
    const method = validateMethod(clone(methodSnapshot || DEFAULT_METHOD));
    const defaults = method.defaults, weights = method.weights;
    const claim = cleanText(payload.claim, 'claim', true);
    const fallback = {
      source_type: cleanChoice(payload.source_type, 'source_type', Object.keys(weights.source_type), defaults.source_type),
      evidence_strength: cleanChoice(payload.evidence_strength, 'evidence_strength', Object.keys(weights.evidence_strength), defaults.evidence_strength),
      source_count: cleanSourceCount(payload.source_count, defaults.source_count)
    };
    const ledger = buildEvidenceLedger(payload, claim, method, fallback);
    const derived = ledger.derived_scoring_inputs;
    let sourceType, evidenceStrength, sourceCount;
    if (derived.ledger_applied) {
      ['source_type','evidence_strength','source_count'].forEach(function (field) {
        if (Object.prototype.hasOwnProperty.call(payload, field) && payload[field] !== undefined && payload[field] !== null && payload[field] !== '' && fallback[field] !== derived[field]) {
          throw new NarrativeRiskValidationError(field + ' conflicts with the value derived from the evidence ledger: ' + derived[field]);
        }
      });
      sourceType = derived.source_type; evidenceStrength = derived.evidence_strength; sourceCount = derived.source_count;
    } else { sourceType = fallback.source_type; evidenceStrength = fallback.evidence_strength; sourceCount = fallback.source_count; }
    return {
      normalized: {
        claim: claim, source_type: sourceType, evidence_strength: evidenceStrength,
        uncertainty: cleanChoice(payload.uncertainty, 'uncertainty', Object.keys(weights.three_level_scale), defaults.uncertainty),
        narrative_volatility: cleanChoice(payload.narrative_volatility, 'narrative_volatility', Object.keys(weights.three_level_scale), defaults.narrative_volatility),
        stakeholder_pressure: cleanChoice(payload.stakeholder_pressure, 'stakeholder_pressure', Object.keys(weights.three_level_scale), defaults.stakeholder_pressure),
        time_sensitivity: cleanChoice(payload.time_sensitivity, 'time_sensitivity', Object.keys(weights.three_level_scale), defaults.time_sensitivity),
        consequences: cleanChoice(payload.consequences, 'consequences', Object.keys(weights.consequences), defaults.consequences),
        review_status: cleanChoice(payload.review_status, 'review_status', Object.keys(weights.review_status), defaults.review_status),
        source_count: sourceCount,
        method_notes: cleanText(payload.method_notes === undefined ? defaults.method_notes : payload.method_notes, 'method_notes', false)
      },
      ledger: ledger
    };
  }
  function normalizeInput(payload, methodSnapshot) { return normalizePayload(payload, methodSnapshot).normalized; }
  function sourceCountWeight(count, ranges) {
    for (const item of ranges) if (count >= item.minimum && (item.maximum === null || count <= item.maximum)) return item.weight;
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
    rules.forEach(function (rule) { if (evaluateRule(rule, normalized, score, output)) output.push(rule.text); });
    return output;
  }
  function appendUnique(target, values) { values.forEach(function (value) { if (!target.includes(value)) target.push(value); }); }
  function scoreNarrativeRisk(payload, methodSnapshot) {
    const method = validateMethod(clone(methodSnapshot || DEFAULT_METHOD));
    const result = normalizePayload(payload, method);
    const normalized = result.normalized, ledger = result.ledger;
    if (!NARRATIVE_MAP || typeof NARRATIVE_MAP.buildNarrativeMap !== 'function') throw new NarrativeRiskValidationError('narrative map engine is unavailable');
    const narrativeMap = NARRATIVE_MAP.buildNarrativeMap(payload, { narrative_claim:normalized.claim, evidence_ledger:ledger, uncertainty:normalized.uncertainty, evidence_strength:normalized.evidence_strength });
    const components = {};
    method.algorithm.component_order.forEach(function (key) {
      const metadata = method.components[key], inputValue = normalized[metadata.input_field];
      const weight = metadata.weight_table === 'source_count_penalties' ? sourceCountWeight(inputValue, method.weights.source_count_penalties) : method.weights[metadata.weight_table][inputValue];
      components[key] = { input_value:inputValue, weight:weight, rationale:metadata.rationale, remediation:metadata.remediation };
    });
    const rawTotal = Object.values(components).reduce(function (sum, item) { return sum + item.weight; }, 0);
    const scaledScore = Number((rawTotal * method.algorithm.multiplier).toFixed(6));
    const riskScore = Math.max(method.algorithm.minimum_score, Math.min(method.algorithm.maximum_score, Math.floor(scaledScore + 0.5)));
    const threshold = clone(method.algorithm.thresholds.find(function (item) { return riskScore >= item.minimum && riskScore <= item.maximum; }));
    if (!threshold) throw new NarrativeRiskValidationError('method_snapshot thresholds do not cover the calculated score');
    const flags = applyRules(method.interpretation.flag_rules, normalized, riskScore);
    const actions = applyRules(method.interpretation.action_rules, normalized, riskScore);
    const ledgerNotes = ledgerInterpretation(ledger, method);
    const mapNotes = NARRATIVE_MAP.narrativeMapInterpretation(narrativeMap);
    appendUnique(flags, ledgerNotes.flags); appendUnique(actions, ledgerNotes.actions);
    appendUnique(flags, mapNotes.flags); appendUnique(actions, mapNotes.actions);
    return {
      normalized_input:normalized,
      evidence_ledger:ledger,
      narrative_map:narrativeMap,
      calculations:{ components:components, raw_total:rawTotal, multiplier:method.algorithm.multiplier, scaled_score:scaledScore, risk_score:riskScore, threshold:threshold },
      interpretation:{ risk_level:threshold.level, flags:flags, review_actions:actions, decision_note:method.interpretation.decision_notes[threshold.level] }
    };
  }

  function randomUuid() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') return globalThis.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (character) {
      const random = Math.floor(Math.random() * 16); const value = character === 'x' ? random : ((random & 0x3) | 0x8); return value.toString(16);
    });
  }
  function urnUuid(value, field) {
    const candidate = value || ('urn:uuid:' + randomUuid());
    if (typeof candidate !== 'string' || !/^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(candidate)) throw new NarrativeRiskValidationError(field + ' must be a urn:uuid identifier');
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
    return { status:cleanChoice(source.status, 'human_decision.status', HUMAN_STATUS, 'draft'), disposition:cleanChoice(source.disposition, 'human_decision.disposition', HUMAN_DISPOSITIONS, 'undecided'), reviewer_id:reviewerId, reviewer_name:reviewerName, reviewed_at:reviewedAt, notes:cleanText(source.notes === undefined ? '' : source.notes, 'human_decision.notes', false) };
  }
  function buildNarrativeRiskRecord(payload, options) {
    const opts = options || {}, method = validateMethod(clone(opts.method_snapshot || DEFAULT_METHOD));
    const analysis = scoreNarrativeRisk(payload, method);
    const generatedAt = opts.generated_at ? validateDateTime(opts.generated_at, 'generated_at') : new Date().toISOString();
    const record = {
      record_type:RECORD_TYPE,
      contract:{ contract_id:CONTRACT_ID, contract_version:VERSION },
      identifiers:{ record_id:urnUuid(opts.record_id, 'record_id'), case_id:urnUuid(opts.case_id, 'case_id'), method_id:METHOD_ID, schema_id:SCHEMA_ID, input_schema_id:INPUT_SCHEMA_ID, ledger_schema_id:LEDGER_SCHEMA_ID, narrative_map_schema_id:NARRATIVE_MAP_SCHEMA_ID },
      generated_at:generatedAt,
      normalized_input:analysis.normalized_input,
      evidence_ledger:analysis.evidence_ledger,
      narrative_map:analysis.narrative_map,
      method_snapshot:method,
      method_snapshot_sha256:digest(method),
      calculations:analysis.calculations,
      interpretation:analysis.interpretation,
      human_decision:normalizeHumanDecision(opts.human_decision)
    };
    if (opts.migration !== undefined && opts.migration !== null) record.migration = clone(opts.migration);
    record.reproducibility = { canonical_input_sha256:digest(record.normalized_input), evidence_ledger_sha256:digest(record.evidence_ledger), narrative_map_sha256:digest(record.narrative_map), record_payload_sha256:digest(record) };
    return record;
  }
  function ledgerInputFromRecord(record) {
    const ledger = record.evidence_ledger;
    const evidence = clone(ledger.evidence_items).map(function (item) { delete item.excerpt_sha256; return item; });
    return { claims:clone(ledger.claims), sources:clone(ledger.sources), evidence_items:evidence, relationships:clone(ledger.relationships) };
  }
  function reproduceNarrativeRiskRecord(record) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) throw new NarrativeRiskValidationError('record must be a JSON object');
    if (digest(record.method_snapshot) !== record.method_snapshot_sha256) throw new NarrativeRiskValidationError('method_snapshot_sha256 does not match the embedded method snapshot');
    const payload = Object.assign({}, clone(record.normalized_input), ledgerInputFromRecord(record), NARRATIVE_MAP.narrativeMapInputFromRecord(record));
    return buildNarrativeRiskRecord(payload, { generated_at:record.generated_at, record_id:record.identifiers.record_id, case_id:record.identifiers.case_id, human_decision:record.human_decision, method_snapshot:record.method_snapshot, migration:record.migration });
  }
  function verifyRecordReproducibility(record) {
    const payload = clone(record), reproducibility = payload.reproducibility; delete payload.reproducibility;
    const reproduced = reproduceNarrativeRiskRecord(record);
    return {
      exact_match:canonicalJson(reproduced) === canonicalJson(record),
      method_snapshot_hash_match:digest(record.method_snapshot) === record.method_snapshot_sha256,
      canonical_input_hash_match:digest(record.normalized_input) === reproducibility.canonical_input_sha256,
      evidence_ledger_hash_match:digest(record.evidence_ledger) === reproducibility.evidence_ledger_sha256,
      narrative_map_hash_match:digest(record.narrative_map) === reproducibility.narrative_map_sha256,
      record_payload_hash_match:digest(payload) === reproducibility.record_payload_sha256,
      record_id:record.identifiers.record_id, method_id:record.identifiers.method_id, method_version:record.method_snapshot.method_version,
      schema_id:record.identifiers.schema_id, ledger_schema_id:record.identifiers.ledger_schema_id, narrative_map_schema_id:record.identifiers.narrative_map_schema_id
    };
  }

  return {
    VERSION:VERSION, RECORD_TYPE:RECORD_TYPE, CONTRACT_ID:CONTRACT_ID, METHOD_ID:METHOD_ID, SCHEMA_ID:SCHEMA_ID,
    INPUT_SCHEMA_ID:INPUT_SCHEMA_ID, LEDGER_SCHEMA_ID:LEDGER_SCHEMA_ID, NARRATIVE_MAP_SCHEMA_ID:NARRATIVE_MAP_SCHEMA_ID, METHOD_SNAPSHOT:clone(DEFAULT_METHOD),
    NarrativeRiskValidationError:NarrativeRiskValidationError, canonicalJson:canonicalJson, sha256:sha256, digest:digest,
    stableLedgerId:stableLedgerId, harvardCitation:harvardCitation, normalizeInput:normalizeInput,
    buildEvidenceLedger:buildEvidenceLedger, normalizeHumanDecision:normalizeHumanDecision,
    scoreNarrativeRisk:scoreNarrativeRisk, buildNarrativeRiskRecord:buildNarrativeRiskRecord,
    reproduceNarrativeRiskRecord:reproduceNarrativeRiskRecord, verifyRecordReproducibility:verifyRecordReproducibility
  };
});
