(function () {
  'use strict';
  const engine = window.CatalystNarrativeRisk;
  if (!engine) return;
  const STORAGE_KEY = 'catalyst_narrative_risk_workspace_v1_5_0';
  const STAGES = ['intake', 'domain', 'editorial', 'legal', 'compliance', 'final'];
  const REQUIRED = new Set(['intake', 'domain', 'editorial', 'final']);
  const ROLE_BY_STAGE = { intake: 'reviewer', domain: 'domain_reviewer', editorial: 'editorial_reviewer', legal: 'legal_reviewer', compliance: 'compliance_reviewer', final: 'final_approver' };
  const BLOCKING_RESTRICTIONS = new Set(['internal_only', 'embargoed', 'no_public_claim', 'legal_review_required']);

  function uuid() {
    const value = globalThis.crypto && crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 3 | 8)).toString(16);
    });
    return 'urn:uuid:' + value;
  }
  function now() { return new Date().toISOString(); }
  function isoLocal(value) { return value ? new Date(value).toISOString() : null; }
  function lines(value) { return String(value || '').split(/\r?\n/).map(function (item) { return item.trim(); }).filter(Boolean); }
  function selectedValues(element) { return Array.from(element.selectedOptions || []).map(function (option) { return option.value; }); }
  function load() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{"cases":{},"saved_views":[]}');
      if (!parsed.cases || typeof parsed.cases !== 'object') parsed.cases = {};
      if (!Array.isArray(parsed.saved_views)) parsed.saved_views = [];
      Object.values(parsed.cases).forEach(normalizeCaseItem);
      return parsed;
    } catch (error) { return { cases: {}, saved_views: [] }; }
  }
  function normalizeCaseItem(item) {
    item.revisions = Array.isArray(item.revisions) ? item.revisions : [];
    item.review_events = Array.isArray(item.review_events) ? item.review_events : [];
    item.activity = Array.isArray(item.activity) ? item.activity : [];
    item.governance_workflow = item.governance_workflow || null;
    item.review_assignments = Array.isArray(item.review_assignments) ? item.review_assignments : [];
    item.governance_decisions = Array.isArray(item.governance_decisions) ? item.governance_decisions : [];
    refreshCounts(item);
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
      bundle_type: 'catalyst_narrative_risk_case_bundle', bundle_version: '1.5.0', exported_at: now(),
      case: caseItem.case, revisions: caseItem.revisions, review_events: caseItem.review_events,
      activity: caseItem.activity, governance_workflow: caseItem.governance_workflow,
      review_assignments: caseItem.review_assignments, governance_decisions: caseItem.governance_decisions
    };
    base.bundle_sha256 = engine.digest(base); return base;
  }
  function addActivity(item, eventType, entityId, payload, createdAt) {
    const next = item.activity.length ? item.activity[item.activity.length - 1].activity_id + 1 : 1;
    item.activity.push({ activity_id: next, case_id: item.case.case_id, event_type: eventType, entity_id: entityId || null, payload: payload || {}, created_at: createdAt || now() });
  }
  function latestFinal(item) {
    return item.governance_decisions.slice().reverse().find(function (decision) { return decision.stage === 'final'; }) || null;
  }
  function refreshWorkflow(item) {
    const workflow = item.governance_workflow;
    if (!workflow) return;
    const final = latestFinal(item);
    workflow.assignment_count = item.review_assignments.length;
    workflow.decision_count = item.governance_decisions.length;
    workflow.required_assignments_complete = Array.from(REQUIRED).every(function (stage) {
      return item.review_assignments.some(function (assignment) { return assignment.stage === stage && ['completed', 'waived'].includes(assignment.status); });
    });
    workflow.final_disposition = final ? final.disposition : null;
    workflow.approval_valid_until = final ? final.valid_until : null;
    workflow.reassessment_at = final ? final.reassessment_at : null;
    workflow.governance_flags = [];
    const stamp = Date.now();
    if (workflow.status === 'approved' && workflow.approval_valid_until && Date.parse(workflow.approval_valid_until) < stamp) {
      workflow.status = 'expired'; workflow.governance_flags.push('approval_expired');
    }
    if (workflow.reassessment_at && Date.parse(workflow.reassessment_at) < stamp) workflow.governance_flags.push('reassessment_due');
    if (item.review_assignments.some(function (assignment) { return assignment.required && ['pending', 'accepted'].includes(assignment.status) && assignment.due_at && Date.parse(assignment.due_at) < stamp; })) workflow.governance_flags.push('required_review_overdue');
    const restrictions = final ? final.publication_restrictions : [];
    workflow.publication_allowed = workflow.status === 'approved' && final && ['approve', 'approve_with_conditions'].includes(final.disposition) && !restrictions.some(function (restriction) { return BLOCKING_RESTRICTIONS.has(restriction); }) && !workflow.governance_flags.includes('reassessment_due');
    workflow.updated_at = item.case.updated_at;
  }
  function refreshCounts(item) {
    item.case.current_revision = item.revisions.length;
    item.case.revision_count = item.revisions.length;
    item.case.review_event_count = item.review_events.length;
    item.case.latest_record_id = item.revisions.length ? item.revisions[item.revisions.length - 1].record_id : null;
    item.case.assignment_count = item.review_assignments ? item.review_assignments.length : 0;
    item.case.governance_decision_count = item.governance_decisions ? item.governance_decisions.length : 0;
    item.case.updated_at = item.activity.length ? item.activity[item.activity.length - 1].created_at : item.case.updated_at;
    refreshWorkflow(item);
    const workflow = item.governance_workflow;
    item.case.workflow_status = workflow ? workflow.status : null;
    item.case.current_stage = workflow ? workflow.current_stage : null;
    item.case.final_disposition = workflow ? workflow.final_disposition : null;
    item.case.approval_valid_until = workflow ? workflow.approval_valid_until : null;
    item.case.reassessment_at = workflow ? workflow.reassessment_at : null;
    item.case.publication_allowed = workflow ? workflow.publication_allowed : false;
  }
  function caseCard(root, item) {
    const card = document.createElement('article'); card.className = 'cnrisk-workspace__case';
    const heading = document.createElement('h4'); heading.textContent = item.case.title;
    const meta = document.createElement('p'); meta.textContent = item.case.status.replaceAll('_', ' ') + ' · ' + item.case.priority + ' · ' + item.case.revision_count + ' revision(s)' + (item.case.workflow_status ? ' · ' + item.case.workflow_status.replaceAll('_', ' ') : '');
    const claim = document.createElement('p'); claim.textContent = item.revisions.length ? item.revisions[item.revisions.length - 1].record.normalized_input.claim : 'No analytical revision yet.';
    const actions = document.createElement('div'); actions.className = 'cnrisk-workspace__actions';
    const open = document.createElement('button'); open.type = 'button'; open.textContent = 'Open'; open.addEventListener('click', function () { openCase(root, item.case.case_id); });
    const exportButton = document.createElement('button'); exportButton.type = 'button'; exportButton.textContent = 'Export'; exportButton.addEventListener('click', function () { download('narrative-risk-case-v1.5.0.json', bundle(item)); });
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
    renderDetail(root, item); renderGovernance(root, item);
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
      item.review_events.forEach(function (event) { const p = document.createElement('p'); p.textContent = event.event_type.replaceAll('_', ' ') + ': ' + event.body; reviews.appendChild(p); }); detail.appendChild(reviews);
    }
  }
  function renderGovernance(root, item) {
    refreshCounts(item);
    const summary = root.querySelector('[data-cnrisk-governance-summary]');
    const assignments = root.querySelector('[data-cnrisk-governance-assignments]');
    const decisions = root.querySelector('[data-cnrisk-governance-decisions]'); assignments.innerHTML = ''; decisions.innerHTML = '';
    if (!item.governance_workflow) { summary.textContent = 'No governance workflow started.'; return; }
    const workflow = item.governance_workflow;
    summary.textContent = workflow.status.replaceAll('_', ' ') + ' · current stage ' + workflow.current_stage + ' · ' + workflow.assignment_count + ' assignment(s) · publication ' + (workflow.publication_allowed ? 'allowed' : 'not allowed') + (workflow.governance_flags.length ? ' · ' + workflow.governance_flags.join(', ') : '');
    item.review_assignments.forEach(function (assignment) {
      const block = document.createElement('div'); block.className = 'cnrisk-workspace__governance-item';
      block.textContent = assignment.stage + ' · ' + assignment.reviewer_id + ' · ' + assignment.reviewer_role.replaceAll('_', ' ') + ' · ' + assignment.status;
      assignments.appendChild(block);
    });
    item.governance_decisions.forEach(function (decision) {
      const block = document.createElement('div'); block.className = 'cnrisk-workspace__governance-item';
      const badge = document.createElement('span'); badge.className = 'cnrisk-workspace__badge'; badge.textContent = decision.disposition.replaceAll('_', ' ');
      const text = document.createElement('p'); text.textContent = decision.stage + ' · ' + decision.decided_by + ' · ' + decision.rationale;
      block.append(badge, text); decisions.appendChild(block);
    });
  }
  function createOrRevise(root, form) {
    const state = load(); const data = Object.fromEntries(new FormData(form).entries());
    const caseId = root.dataset.currentCaseId || uuid(); const stamp = now(); let item = state.cases[caseId];
    if (!item) {
      item = {
        case: { case_id: caseId, organization_id: null, project_id: null, title: data.case_title.trim(), summary: data.case_summary.trim(), status: data.case_status, priority: data.case_priority, tags: tags(data.case_tags), archived: false, archived_at: null, created_at: stamp, updated_at: stamp, current_revision: 0, latest_record_id: null, revision_count: 0, review_event_count: 0, assignment_count: 0, governance_decision_count: 0, workflow_status: null, current_stage: null, final_disposition: null, approval_valid_until: null, reassessment_at: null, publication_allowed: false },
        revisions: [], review_events: [], activity: [], governance_workflow: null, review_assignments: [], governance_decisions: []
      };
      addActivity(item, 'case_created', caseId, { title: item.case.title }, stamp); state.cases[caseId] = item;
    } else {
      item.case.title = data.case_title.trim(); item.case.summary = data.case_summary.trim(); item.case.status = data.case_status; item.case.priority = data.case_priority; item.case.tags = tags(data.case_tags);
      addActivity(item, 'case_updated', caseId, { status: item.case.status, priority: item.case.priority, tags: item.case.tags }, stamp);
    }
    const record = engine.buildNarrativeRiskRecord({ claim: data.claim, uncertainty: data.uncertainty, narrative_volatility: data.narrative_volatility, stakeholder_pressure: data.stakeholder_pressure, time_sensitivity: data.time_sensitivity, consequences: data.consequences, review_status: data.review_status, method_notes: data.method_notes }, { case_id: caseId });
    const revisionId = uuid(); const number = item.revisions.length + 1;
    item.revisions.push({ revision_id: revisionId, case_id: caseId, revision_number: number, record_id: record.identifiers.record_id, record_sha256: engine.digest(record), created_at: stamp, created_by: null, change_note: data.change_note.trim(), record: record });
    addActivity(item, 'revision_added', revisionId, { revision_number: number, record_id: record.identifiers.record_id, record_sha256: engine.digest(record) }, stamp);
    refreshCounts(item); save(state); root.dataset.currentCaseId = caseId; renderList(root); renderDetail(root, item); renderGovernance(root, item);
  }
  function addReview(root) {
    const caseId = root.dataset.currentCaseId; if (!caseId) throw new Error('Open or create a case before adding review activity.');
    const state = load(); const item = state.cases[caseId]; const body = root.querySelector('[data-cnrisk-review-body]').value.trim(); if (!body) throw new Error('Review comment is required.');
    const event = { event_id: uuid(), case_id: caseId, revision_id: item.revisions.length ? item.revisions[item.revisions.length - 1].revision_id : null, event_type: 'comment', author_id: null, author_name: null, body: body, created_at: now(), metadata: {} };
    item.review_events.push(event); addActivity(item, 'review_event_added', event.event_id, { event_type: event.event_type, revision_id: event.revision_id }); refreshCounts(item); save(state); root.querySelector('[data-cnrisk-review-body]').value = ''; renderDetail(root, item); renderList(root);
  }
  function startGovernance(root) {
    const id = root.dataset.currentCaseId; if (!id) throw new Error('Open or create a case before starting governance.');
    const state = load(); const item = state.cases[id]; if (!item.revisions.length) throw new Error('Save an analytical revision first.'); if (item.governance_workflow) throw new Error('This browser case already has a governance workflow.');
    const stamp = now(); const workflowId = uuid();
    item.governance_workflow = { workflow_id: workflowId, case_id: id, revision_id: item.revisions[item.revisions.length - 1].revision_id, template_id: null, template_snapshot: { name: 'Standard Narrative Risk Review', description: 'Staged browser review aligned with v1.5.0.', stages: STAGES.map(function (stage) { return { stage: stage, required: REQUIRED.has(stage), required_role: ROLE_BY_STAGE[stage], instructions: 'Review the ' + stage + ' stage.' }; }), default_due_days: 14, escalation_days: 3 }, status: 'active', current_stage: 'intake', started_at: stamp, due_at: null, completed_at: null, created_by: null, updated_at: stamp, assignment_count: 0, decision_count: 0, required_assignments_complete: false, final_disposition: null, approval_valid_until: null, reassessment_at: null, publication_allowed: false, governance_flags: [] };
    item.case.status = 'in_review'; addActivity(item, 'governance_workflow_started', workflowId, { revision_id: item.governance_workflow.revision_id, current_stage: 'intake' }, stamp); refreshCounts(item); save(state); renderGovernance(root, item); renderList(root);
  }
  function assignReviewer(root) {
    const id = root.dataset.currentCaseId; if (!id) throw new Error('Open a case first.'); const state = load(); const item = state.cases[id]; if (!item.governance_workflow) throw new Error('Start the governance workflow first.');
    const stage = root.querySelector('[data-cnrisk-assignment-stage]').value; const reviewerId = root.querySelector('[data-cnrisk-reviewer-id]').value.trim(); if (!reviewerId) throw new Error('Reviewer identifier is required.');
    const stamp = now(); const assignmentId = uuid(); const due = isoLocal(root.querySelector('[data-cnrisk-assignment-due]').value);
    const assignment = { assignment_id: assignmentId, case_id: id, revision_id: item.governance_workflow.revision_id, workflow_id: item.governance_workflow.workflow_id, stage: stage, reviewer_id: reviewerId, reviewer_name: null, reviewer_role: root.querySelector('[data-cnrisk-reviewer-role]').value, status: 'pending', required: REQUIRED.has(stage), instructions: 'Complete the ' + stage + ' review.', created_at: stamp, created_by: null, due_at: due, accepted_at: null, completed_at: null, escalated_at: null };
    item.review_assignments.push(assignment); addActivity(item, 'reviewer_assigned', assignmentId, { stage: stage, reviewer_id: reviewerId, required: assignment.required }, stamp); refreshCounts(item); save(state); renderGovernance(root, item); renderList(root);
  }
  function addDecision(root) {
    const id = root.dataset.currentCaseId; if (!id) throw new Error('Open a case first.'); const state = load(); const item = state.cases[id]; const workflow = item.governance_workflow; if (!workflow) throw new Error('Start the governance workflow first.');
    const stage = root.querySelector('[data-cnrisk-decision-stage]').value; const disposition = root.querySelector('[data-cnrisk-disposition]').value; const decidedBy = root.querySelector('[data-cnrisk-decided-by]').value.trim(); const rationale = root.querySelector('[data-cnrisk-decision-rationale]').value.trim(); if (!decidedBy || !rationale) throw new Error('Decision maker and rationale are required.');
    const assignment = item.review_assignments.find(function (entry) { return entry.stage === stage && entry.reviewer_id === decidedBy && !['completed', 'waived'].includes(entry.status); });
    if (REQUIRED.has(stage) && !assignment) throw new Error('Required stages need a matching reviewer assignment.');
    const conditions = lines(root.querySelector('[data-cnrisk-conditions]').value); const wording = lines(root.querySelector('[data-cnrisk-required-wording]').value); const restrictions = selectedValues(root.querySelector('[data-cnrisk-publication-restrictions]')); const disclosures = lines(root.querySelector('[data-cnrisk-disclosures]').value);
    if (disposition === 'approve_with_conditions' && !(conditions.length || wording.length || restrictions.length || disclosures.length)) throw new Error('Conditional approval requires a condition, wording requirement, restriction, or disclosure.');
    if (stage === 'final' && ['approve', 'approve_with_conditions'].includes(disposition)) {
      const complete = Array.from(REQUIRED).every(function (requiredStage) { return requiredStage === 'final' ? !!assignment : item.review_assignments.some(function (entry) { return entry.stage === requiredStage && ['completed', 'waived'].includes(entry.status); }); });
      if (!complete) throw new Error('Complete or waive all required stage assignments before final approval.');
    }
    const stamp = now(); const decisionId = uuid();
    const decision = { decision_id: decisionId, case_id: id, revision_id: workflow.revision_id, workflow_id: workflow.workflow_id, assignment_id: assignment ? assignment.assignment_id : null, stage: stage, disposition: disposition, decided_by: decidedBy, decided_by_name: null, decider_role: root.querySelector('[data-cnrisk-decider-role]').value, decided_at: stamp, rationale: rationale, conditions: conditions, required_wording: wording, publication_restrictions: restrictions, disclosures: disclosures, valid_until: isoLocal(root.querySelector('[data-cnrisk-valid-until]').value), reassessment_at: isoLocal(root.querySelector('[data-cnrisk-reassessment-at]').value), supersedes_decision_id: null };
    item.governance_decisions.push(decision); if (assignment) { assignment.status = disposition === 'waive' ? 'waived' : 'completed'; assignment.completed_at = stamp; }
    const index = STAGES.indexOf(stage); workflow.current_stage = index < STAGES.length - 1 && ['approve', 'approve_with_conditions', 'waive'].includes(disposition) ? STAGES[index + 1] : stage;
    if (disposition === 'revise') workflow.status = 'changes_required'; else if (disposition === 'reject') { workflow.status = 'rejected'; workflow.completed_at = stamp; item.case.status = 'closed'; } else if (stage === 'final' && ['approve', 'approve_with_conditions'].includes(disposition)) { workflow.status = 'approved'; workflow.completed_at = stamp; workflow.current_stage = 'final'; item.case.status = 'approved'; } else workflow.status = 'active';
    addActivity(item, 'governance_decision_added', decisionId, { stage: stage, disposition: disposition, workflow_status: workflow.status }, stamp); refreshCounts(item); save(state); renderGovernance(root, item); renderList(root);
  }
  function importBundle(root, file) {
    const reader = new FileReader(); reader.onload = function () {
      try {
        const data = JSON.parse(reader.result); if (data.bundle_type !== 'catalyst_narrative_risk_case_bundle' || data.bundle_version !== '1.5.0') throw new Error('Not a v1.5.0 narrative-risk case bundle.');
        const expected = data.bundle_sha256; const unsigned = Object.assign({}, data); delete unsigned.bundle_sha256; if (engine.digest(unsigned) !== expected) throw new Error('Bundle checksum does not match.');
        const state = load(); const caseId = data.case.case_id; if (state.cases[caseId]) throw new Error('A case with this identifier already exists.');
        state.cases[caseId] = { case: data.case, revisions: data.revisions, review_events: data.review_events, activity: data.activity, governance_workflow: data.governance_workflow, review_assignments: data.review_assignments, governance_decisions: data.governance_decisions }; normalizeCaseItem(state.cases[caseId]); save(state); renderList(root); openCase(root, caseId);
      } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; }
    }; reader.readAsText(file);
  }
  function guarded(root, callback, success) { try { callback(); root.querySelector('[data-cnrisk-workspace-message]').textContent = success || ''; } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; } }
  function init(root) {
    const form = root.querySelector('[data-cnrisk-workspace-form]');
    form.addEventListener('submit', function (event) { event.preventDefault(); guarded(root, function () { createOrRevise(root, form); }, 'Case revision saved in this browser.'); });
    root.querySelector('[data-cnrisk-new-case]').addEventListener('click', function () { delete root.dataset.currentCaseId; form.reset(); root.querySelector('[data-cnrisk-workspace-detail]').innerHTML = '<p>Start a new case or open an existing one.</p>'; root.querySelector('[data-cnrisk-governance-summary]').textContent = 'No governance workflow started.'; root.querySelector('[data-cnrisk-governance-assignments]').innerHTML = ''; root.querySelector('[data-cnrisk-governance-decisions]').innerHTML = ''; });
    root.querySelector('[data-cnrisk-workspace-search]').addEventListener('input', function () { renderList(root); });
    root.querySelector('[data-cnrisk-add-review]').addEventListener('click', function () { guarded(root, function () { addReview(root); }, 'Review activity saved.'); });
    root.querySelector('[data-cnrisk-start-governance]').addEventListener('click', function () { guarded(root, function () { startGovernance(root); }, 'Governance workflow started.'); });
    root.querySelector('[data-cnrisk-assign-reviewer]').addEventListener('click', function () { guarded(root, function () { assignReviewer(root); }, 'Reviewer assigned.'); });
    root.querySelector('[data-cnrisk-add-decision]').addEventListener('click', function () { guarded(root, function () { addDecision(root); }, 'Governance decision recorded.'); });
    root.querySelector('[data-cnrisk-assignment-stage]').addEventListener('change', function () { root.querySelector('[data-cnrisk-reviewer-role]').value = ROLE_BY_STAGE[this.value]; root.querySelector('[data-cnrisk-decision-stage]').value = this.value; });
    root.querySelector('[data-cnrisk-archive-case]').addEventListener('click', function () { const id = root.dataset.currentCaseId; if (!id) return; const state = load(); const item = state.cases[id]; item.case.archived = true; item.case.archived_at = now(); addActivity(item, 'case_archived', id, {}); refreshCounts(item); save(state); delete root.dataset.currentCaseId; renderList(root); });
    root.querySelector('[data-cnrisk-import-bundle]').addEventListener('change', function () { if (this.files[0]) importBundle(root, this.files[0]); this.value = ''; });
    renderList(root);
  }
  document.addEventListener('DOMContentLoaded', function () { document.querySelectorAll('[data-cnrisk-workspace]').forEach(init); });
})();
