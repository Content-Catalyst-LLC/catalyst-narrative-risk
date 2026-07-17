(function () {
  'use strict';
  const engine = window.CatalystNarrativeRisk;
  if (!engine) return;
  const STORAGE_KEY = 'catalyst_narrative_risk_workspace_v1_3_0';

  function uuid() {
    const value = globalThis.crypto && crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 3 | 8)).toString(16);
    });
    return 'urn:uuid:' + value;
  }
  function now() { return new Date().toISOString(); }
  function load() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{"cases":{},"saved_views":[]}');
      if (!parsed.cases || typeof parsed.cases !== 'object') parsed.cases = {};
      if (!Array.isArray(parsed.saved_views)) parsed.saved_views = [];
      return parsed;
    } catch (error) { return { cases: {}, saved_views: [] }; }
  }
  function save(state) { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  function tags(value) {
    const seen = new Set();
    return String(value || '').split(',').map(function (tag) { return tag.trim(); }).filter(function (tag) {
      const key = tag.toLowerCase(); if (!tag || seen.has(key)) return false; seen.add(key); return true;
    });
  }
  function download(name, value) {
    const blob = new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  }
  function bundle(caseItem) {
    const base = {
      bundle_type: 'catalyst_narrative_risk_case_bundle', bundle_version: '1.3.0', exported_at: now(),
      case: caseItem.case, revisions: caseItem.revisions, review_events: caseItem.review_events, activity: caseItem.activity
    };
    base.bundle_sha256 = engine.digest(base);
    return base;
  }
  function addActivity(caseItem, eventType, entityId, payload) {
    const next = caseItem.activity.length ? caseItem.activity[caseItem.activity.length - 1].activity_id + 1 : 1;
    caseItem.activity.push({ activity_id: next, case_id: caseItem.case.case_id, event_type: eventType, entity_id: entityId || null, payload: payload || {}, created_at: now() });
  }
  function refreshCounts(caseItem) {
    caseItem.case.current_revision = caseItem.revisions.length;
    caseItem.case.revision_count = caseItem.revisions.length;
    caseItem.case.review_event_count = caseItem.review_events.length;
    caseItem.case.latest_record_id = caseItem.revisions.length ? caseItem.revisions[caseItem.revisions.length - 1].record_id : null;
    caseItem.case.updated_at = now();
  }
  function caseCard(root, caseItem) {
    const card = document.createElement('article'); card.className = 'cnrisk-workspace__case';
    const heading = document.createElement('h4'); heading.textContent = caseItem.case.title;
    const meta = document.createElement('p'); meta.textContent = caseItem.case.status.replaceAll('_', ' ') + ' · ' + caseItem.case.priority + ' · ' + caseItem.case.revision_count + ' revision(s)';
    const claim = document.createElement('p');
    claim.textContent = caseItem.revisions.length ? caseItem.revisions[caseItem.revisions.length - 1].record.normalized_input.claim : 'No analytical revision yet.';
    const actions = document.createElement('div'); actions.className = 'cnrisk-workspace__actions';
    const open = document.createElement('button'); open.type = 'button'; open.textContent = 'Open'; open.addEventListener('click', function () { openCase(root, caseItem.case.case_id); });
    const exportButton = document.createElement('button'); exportButton.type = 'button'; exportButton.textContent = 'Export'; exportButton.addEventListener('click', function () { download('narrative-risk-case-v1.3.0.json', bundle(caseItem)); });
    actions.append(open, exportButton); card.append(heading, meta, claim, actions); return card;
  }
  function renderList(root) {
    const state = load(); const list = root.querySelector('[data-cnrisk-workspace-list]'); list.innerHTML = '';
    const query = root.querySelector('[data-cnrisk-workspace-search]').value.trim().toLowerCase();
    const values = Object.values(state.cases).filter(function (item) {
      return !item.case.archived && (!query || item.case.title.toLowerCase().includes(query) || item.case.summary.toLowerCase().includes(query) || item.case.tags.join(' ').toLowerCase().includes(query));
    }).sort(function (a, b) { return b.case.updated_at.localeCompare(a.case.updated_at); });
    if (!values.length) { const empty = document.createElement('p'); empty.textContent = 'No active cases match this view.'; list.appendChild(empty); return; }
    values.forEach(function (item) { list.appendChild(caseCard(root, item)); });
  }
  function openCase(root, caseId) {
    const state = load(); const item = state.cases[caseId]; if (!item) return;
    root.dataset.currentCaseId = caseId;
    root.querySelector('[name="case_title"]').value = item.case.title;
    root.querySelector('[name="case_summary"]').value = item.case.summary;
    root.querySelector('[name="case_status"]').value = item.case.status;
    root.querySelector('[name="case_priority"]').value = item.case.priority;
    root.querySelector('[name="case_tags"]').value = item.case.tags.join(', ');
    if (item.revisions.length) root.querySelector('[name="claim"]').value = item.revisions[item.revisions.length - 1].record.normalized_input.claim;
    renderDetail(root, item);
  }
  function renderDetail(root, item) {
    const detail = root.querySelector('[data-cnrisk-workspace-detail]'); detail.innerHTML = '';
    const title = document.createElement('h4'); title.textContent = item.case.title;
    const meta = document.createElement('p'); meta.textContent = item.case.case_id + ' · ' + item.case.status + ' · updated ' + item.case.updated_at;
    detail.append(title, meta);
    item.revisions.slice().reverse().forEach(function (revision) {
      const block = document.createElement('section');
      const heading = document.createElement('strong'); heading.textContent = 'Revision ' + revision.revision_number + ' · score ' + revision.record.calculations.risk_score + ' · ' + revision.record.interpretation.risk_level;
      const claim = document.createElement('p'); claim.textContent = revision.record.normalized_input.claim;
      const note = document.createElement('small'); note.textContent = revision.change_note || 'No change note.';
      block.append(heading, claim, note); detail.appendChild(block);
    });
    if (item.review_events.length) {
      const reviews = document.createElement('div'); reviews.className = 'cnrisk-workspace__reviews';
      const heading = document.createElement('h5'); heading.textContent = 'Review activity'; reviews.appendChild(heading);
      item.review_events.forEach(function (event) { const p = document.createElement('p'); p.textContent = event.event_type.replaceAll('_', ' ') + ': ' + event.body; reviews.appendChild(p); });
      detail.appendChild(reviews);
    }
  }
  function createOrRevise(root, form) {
    const state = load(); const data = Object.fromEntries(new FormData(form).entries());
    let caseId = root.dataset.currentCaseId || uuid(); const stamp = now(); let item = state.cases[caseId];
    if (!item) {
      item = {
        case: { case_id: caseId, organization_id: null, project_id: null, title: data.case_title.trim(), summary: data.case_summary.trim(), status: data.case_status, priority: data.case_priority, tags: tags(data.case_tags), archived: false, archived_at: null, created_at: stamp, updated_at: stamp, current_revision: 0, latest_record_id: null, revision_count: 0, review_event_count: 0 },
        revisions: [], review_events: [], activity: []
      };
      addActivity(item, 'case_created', caseId, { title: item.case.title }); state.cases[caseId] = item;
    } else {
      item.case.title = data.case_title.trim(); item.case.summary = data.case_summary.trim(); item.case.status = data.case_status; item.case.priority = data.case_priority; item.case.tags = tags(data.case_tags);
      addActivity(item, 'case_updated', caseId, { status: item.case.status, priority: item.case.priority, tags: item.case.tags });
    }
    const record = engine.buildNarrativeRiskRecord({ claim: data.claim, uncertainty: data.uncertainty, narrative_volatility: data.narrative_volatility, stakeholder_pressure: data.stakeholder_pressure, time_sensitivity: data.time_sensitivity, consequences: data.consequences, review_status: data.review_status, method_notes: data.method_notes }, { case_id: caseId });
    const revisionId = uuid(); const number = item.revisions.length + 1;
    item.revisions.push({ revision_id: revisionId, case_id: caseId, revision_number: number, record_id: record.identifiers.record_id, record_sha256: engine.digest(record), created_at: stamp, created_by: null, change_note: data.change_note.trim(), record: record });
    addActivity(item, 'revision_added', revisionId, { revision_number: number, record_id: record.identifiers.record_id, record_sha256: engine.digest(record) });
    refreshCounts(item); save(state); root.dataset.currentCaseId = caseId; renderList(root); renderDetail(root, item);
  }
  function addReview(root) {
    const caseId = root.dataset.currentCaseId; if (!caseId) throw new Error('Open or create a case before adding review activity.');
    const state = load(); const item = state.cases[caseId]; const body = root.querySelector('[data-cnrisk-review-body]').value.trim(); if (!body) throw new Error('Review comment is required.');
    const event = { event_id: uuid(), case_id: caseId, revision_id: item.revisions.length ? item.revisions[item.revisions.length - 1].revision_id : null, event_type: 'comment', author_id: null, author_name: null, body: body, created_at: now(), metadata: {} };
    item.review_events.push(event); addActivity(item, 'review_event_added', event.event_id, { event_type: event.event_type, revision_id: event.revision_id }); refreshCounts(item); save(state); root.querySelector('[data-cnrisk-review-body]').value = ''; renderDetail(root, item); renderList(root);
  }
  function importBundle(root, file) {
    const reader = new FileReader(); reader.onload = function () {
      try {
        const data = JSON.parse(reader.result); if (data.bundle_type !== 'catalyst_narrative_risk_case_bundle' || data.bundle_version !== '1.3.0') throw new Error('Not a v1.3.0 narrative-risk case bundle.');
        const expected = data.bundle_sha256; const unsigned = Object.assign({}, data); delete unsigned.bundle_sha256; if (engine.digest(unsigned) !== expected) throw new Error('Bundle checksum does not match.');
        const state = load(); const caseId = data.case.case_id; if (state.cases[caseId]) throw new Error('A case with this identifier already exists.');
        state.cases[caseId] = { case: data.case, revisions: data.revisions, review_events: data.review_events, activity: data.activity }; save(state); renderList(root); openCase(root, caseId);
      } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; }
    }; reader.readAsText(file);
  }
  function init(root) {
    const form = root.querySelector('[data-cnrisk-workspace-form]');
    form.addEventListener('submit', function (event) { event.preventDefault(); try { createOrRevise(root, form); root.querySelector('[data-cnrisk-workspace-message]').textContent = 'Case revision saved in this browser.'; } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; } });
    root.querySelector('[data-cnrisk-new-case]').addEventListener('click', function () { delete root.dataset.currentCaseId; form.reset(); root.querySelector('[data-cnrisk-workspace-detail]').innerHTML = '<p>Start a new case or open an existing one.</p>'; });
    root.querySelector('[data-cnrisk-workspace-search]').addEventListener('input', function () { renderList(root); });
    root.querySelector('[data-cnrisk-add-review]').addEventListener('click', function () { try { addReview(root); } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; } });
    root.querySelector('[data-cnrisk-archive-case]').addEventListener('click', function () { const id = root.dataset.currentCaseId; if (!id) return; const state = load(); const item = state.cases[id]; item.case.archived = true; item.case.archived_at = now(); addActivity(item, 'case_archived', id, {}); refreshCounts(item); save(state); delete root.dataset.currentCaseId; renderList(root); });
    root.querySelector('[data-cnrisk-import-bundle]').addEventListener('change', function () { if (this.files[0]) importBundle(root, this.files[0]); this.value = ''; });
    renderList(root);
  }
  document.addEventListener('DOMContentLoaded', function () { document.querySelectorAll('[data-cnrisk-workspace]').forEach(init); });
})();
