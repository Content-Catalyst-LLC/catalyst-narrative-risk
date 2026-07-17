(function () {
  'use strict';
  const engine = window.CatalystNarrativeRisk;
  if (!engine) return;
  const STORAGE_KEY = 'catalyst_narrative_risk_workspace_v1_9_0';
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
    item.monitoring_snapshots = Array.isArray(item.monitoring_snapshots) ? item.monitoring_snapshots : [];
    item.monitoring_comparisons = Array.isArray(item.monitoring_comparisons) ? item.monitoring_comparisons : [];
    item.watchlists = Array.isArray(item.watchlists) ? item.watchlists : [];
    item.monitoring_alerts = Array.isArray(item.monitoring_alerts) ? item.monitoring_alerts : [];
    item.site_intelligence_events = Array.isArray(item.site_intelligence_events) ? item.site_intelligence_events : [];
    item.stakeholder_actors = Array.isArray(item.stakeholder_actors) ? item.stakeholder_actors : [];
    item.stakeholder_relationships = Array.isArray(item.stakeholder_relationships) ? item.stakeholder_relationships : [];
    item.stakeholder_incentives = Array.isArray(item.stakeholder_incentives) ? item.stakeholder_incentives : [];
    item.stakeholder_pressures = Array.isArray(item.stakeholder_pressures) ? item.stakeholder_pressures : [];
    item.stakeholder_consequences = Array.isArray(item.stakeholder_consequences) ? item.stakeholder_consequences : [];
    item.catalyst_canvas_handoffs = Array.isArray(item.catalyst_canvas_handoffs) ? item.catalyst_canvas_handoffs : [];
    item.comparison_sets = Array.isArray(item.comparison_sets) ? item.comparison_sets : [];
    item.comparative_evidence_matrices = Array.isArray(item.comparative_evidence_matrices) ? item.comparative_evidence_matrices : [];
    item.scenarios = Array.isArray(item.scenarios) ? item.scenarios : [];
    item.scenario_results = Array.isArray(item.scenario_results) ? item.scenario_results : [];
    item.sensitivity_analyses = Array.isArray(item.sensitivity_analyses) ? item.sensitivity_analyses : [];
    item.decision_studio_handoffs = Array.isArray(item.decision_studio_handoffs) ? item.decision_studio_handoffs : [];
    item.publication_briefings = Array.isArray(item.publication_briefings) ? item.publication_briefings : [];
    item.publication_packages = Array.isArray(item.publication_packages) ? item.publication_packages : [];
    item.public_embeds = Array.isArray(item.public_embeds) ? item.public_embeds : [];
    item.platform_handoffs = Array.isArray(item.platform_handoffs) ? item.platform_handoffs : [];
    item.comparative_portfolio = item.comparative_portfolio || null;
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
      bundle_type: 'catalyst_narrative_risk_case_bundle', bundle_version: '1.9.0', exported_at: now(),
      case: caseItem.case, revisions: caseItem.revisions, review_events: caseItem.review_events,
      activity: caseItem.activity, governance_workflow: caseItem.governance_workflow,
      review_assignments: caseItem.review_assignments, governance_decisions: caseItem.governance_decisions,
      monitoring_snapshots: caseItem.monitoring_snapshots, monitoring_comparisons: caseItem.monitoring_comparisons,
      watchlists: caseItem.watchlists, monitoring_alerts: caseItem.monitoring_alerts,
      site_intelligence_events: caseItem.site_intelligence_events,
      stakeholder_actors: caseItem.stakeholder_actors, stakeholder_relationships: caseItem.stakeholder_relationships,
      stakeholder_incentives: caseItem.stakeholder_incentives, stakeholder_pressures: caseItem.stakeholder_pressures,
      stakeholder_consequences: caseItem.stakeholder_consequences, stakeholder_intelligence: stakeholderSummary(caseItem),
      catalyst_canvas_handoffs: caseItem.catalyst_canvas_handoffs,
      comparison_sets: caseItem.comparison_sets, comparative_evidence_matrices: caseItem.comparative_evidence_matrices,
      scenarios: caseItem.scenarios, scenario_results: caseItem.scenario_results,
      sensitivity_analyses: caseItem.sensitivity_analyses, comparative_portfolio: comparativePortfolio(caseItem),
      decision_studio_handoffs: caseItem.decision_studio_handoffs,
      publication_briefings: caseItem.publication_briefings, publication_packages: caseItem.publication_packages,
      public_embeds: caseItem.public_embeds, platform_handoffs: caseItem.platform_handoffs
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
    item.case.monitoring_snapshot_count = item.monitoring_snapshots.length;
    item.case.watch_count = item.watchlists.filter(function (watch) { return watch.status === 'active'; }).length;
    item.case.open_alert_count = item.monitoring_alerts.filter(function (alert) { return alert.status === 'open'; }).length;
    item.case.last_monitored_at = item.monitoring_snapshots.length ? item.monitoring_snapshots[item.monitoring_snapshots.length - 1].captured_at : null;
    item.case.monitoring_status = item.case.open_alert_count ? 'attention_required' : (item.case.monitoring_snapshot_count ? 'current' : 'not_started');
    const intelligence = stakeholderSummary(item);
    item.case.stakeholder_actor_count = item.stakeholder_actors.length;
    item.case.stakeholder_relationship_count = item.stakeholder_relationships.length;
    item.case.stakeholder_incentive_count = item.stakeholder_incentives.length;
    item.case.stakeholder_pressure_count = item.stakeholder_pressures.length;
    item.case.stakeholder_consequence_count = item.stakeholder_consequences.length;
    item.case.suggested_stakeholder_pressure = intelligence.suggested_stakeholder_pressure;
    item.case.comparison_set_count = item.comparison_sets.length;
    item.case.scenario_count = item.scenarios.length;
    item.case.evaluated_scenario_count = item.scenario_results.length;
    item.case.sensitivity_analysis_count = item.sensitivity_analyses.length;
    item.case.decision_studio_handoff_count = item.decision_studio_handoffs.length;
    item.case.comparative_status = item.scenario_results.length ? 'scenario_ready' : (item.comparison_sets.length ? 'comparison_ready' : 'not_started');
    item.case.publication_briefing_count = item.publication_briefings.length;
    item.case.publication_package_count = item.publication_packages.length;
    item.case.public_embed_count = item.public_embeds.filter(function (embed) { return embed.status === 'active'; }).length;
    item.case.platform_handoff_count = item.platform_handoffs.length;
    item.case.publication_status = item.publication_packages.some(function (pkg) { return pkg.status === 'published'; }) ? 'published' : (item.publication_packages.length ? 'ready' : 'not_started');
    item.comparative_portfolio = comparativePortfolio(item);
  }
  function caseCard(root, item) {
    const card = document.createElement('article'); card.className = 'cnrisk-workspace__case';
    const heading = document.createElement('h4'); heading.textContent = item.case.title;
    const meta = document.createElement('p'); meta.textContent = item.case.status.replaceAll('_', ' ') + ' · ' + item.case.priority + ' · ' + item.case.revision_count + ' revision(s)' + (item.case.workflow_status ? ' · ' + item.case.workflow_status.replaceAll('_', ' ') : '');
    const claim = document.createElement('p'); claim.textContent = item.revisions.length ? item.revisions[item.revisions.length - 1].record.normalized_input.claim : 'No analytical revision yet.';
    const actions = document.createElement('div'); actions.className = 'cnrisk-workspace__actions';
    const open = document.createElement('button'); open.type = 'button'; open.textContent = 'Open'; open.addEventListener('click', function () { openCase(root, item.case.case_id); });
    const exportButton = document.createElement('button'); exportButton.type = 'button'; exportButton.textContent = 'Export'; exportButton.addEventListener('click', function () { download('narrative-risk-case-v1.9.0.json', bundle(item)); });
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
    renderDetail(root, item); renderGovernance(root, item); renderMonitoring(root, item); renderStakeholders(root, item); renderComparative(root, item);
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
        revisions: [], review_events: [], activity: [], governance_workflow: null, review_assignments: [], governance_decisions: [],
        monitoring_snapshots: [], monitoring_comparisons: [], watchlists: [], monitoring_alerts: [], site_intelligence_events: [],
        stakeholder_actors: [], stakeholder_relationships: [], stakeholder_incentives: [], stakeholder_pressures: [], stakeholder_consequences: [], catalyst_canvas_handoffs: [],
        comparison_sets: [], comparative_evidence_matrices: [], scenarios: [], scenario_results: [], sensitivity_analyses: [], comparative_portfolio: null, decision_studio_handoffs: [],
        publication_briefings: [], publication_packages: [], public_embeds: [], platform_handoffs: []
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
    refreshCounts(item); save(state); root.dataset.currentCaseId = caseId; renderList(root); renderDetail(root, item); renderGovernance(root, item); renderComparative(root, item);
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
    item.governance_workflow = { workflow_id: workflowId, case_id: id, revision_id: item.revisions[item.revisions.length - 1].revision_id, template_id: null, template_snapshot: { name: 'Standard Narrative Risk Review', description: 'Staged browser review aligned with v1.9.0.', stages: STAGES.map(function (stage) { return { stage: stage, required: REQUIRED.has(stage), required_role: ROLE_BY_STAGE[stage], instructions: 'Review the ' + stage + ' stage.' }; }), default_due_days: 14, escalation_days: 3 }, status: 'active', current_stage: 'intake', started_at: stamp, due_at: null, completed_at: null, created_by: null, updated_at: stamp, assignment_count: 0, decision_count: 0, required_assignments_complete: false, final_disposition: null, approval_valid_until: null, reassessment_at: null, publication_allowed: false, governance_flags: [] };
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
  function monitoringSnapshot(item, trigger) {
    if (!item.revisions.length) throw new Error('Save an analytical revision before capturing a snapshot.');
    const revision = item.revisions[item.revisions.length - 1]; const record = revision.record; const stamp = now();
    const claims = (record.evidence_ledger.claims || []).map(function (claim) { return { claim_id: claim.claim_id, text: claim.text, claim_type: claim.claim_type, role: claim.role }; });
    const nodes = (record.narrative_map.nodes || []).map(function (node) { return { node_id: node.node_id, text: node.text, node_type: node.node_type, confidence_language: node.confidence_language }; });
    const sources = (record.evidence_ledger.sources || []).map(function (source) { return { source_id: source.source_id, title: source.title, source_type: source.source_type, reference_at: source.accessed_at || null, age_days: null, freshness: source.freshness || 'unknown', content_sha256: source.provenance ? source.provenance.content_sha256 : null }; });
    const counts = { current: 0, aging: 0, stale: 0, unknown: 0 }; sources.forEach(function (source) { counts[source.freshness] = (counts[source.freshness] || 0) + 1; });
    const final = latestFinal(item); const snapshot = {
      snapshot_id: uuid(), snapshot_version: '1.9.0', case_id: item.case.case_id, revision_id: revision.revision_id,
      record_id: revision.record_id, captured_at: stamp, trigger: trigger || 'manual', record_sha256: engine.digest(record),
      risk_score: record.calculations.risk_score, risk_level: record.interpretation.risk_level,
      confidence_state: { evidence_strength: record.normalized_input.evidence_strength, uncertainty: record.normalized_input.uncertainty, review_status: record.normalized_input.review_status },
      claims: claims, narrative_nodes: nodes, narrative_link_ids: (record.narrative_map.links || []).map(function (link) { return link.link_id; }),
      source_ids: sources.map(function (source) { return source.source_id; }), evidence_ids: (record.evidence_ledger.evidence_items || []).map(function (evidence) { return evidence.evidence_id; }),
      freshness_report: { evaluated_at: stamp, status: sources.length ? (counts.stale ? 'stale' : (counts.aging ? 'aging' : 'current')) : 'unknown', source_count: sources.length, counts: counts, stale_ratio: sources.length ? counts.stale / sources.length : 0, sources: sources, reassessment_recommended: !!counts.stale },
      governance_state: { workflow_status: item.governance_workflow ? item.governance_workflow.status : null, final_disposition: final ? final.disposition : null, approval_valid_until: final ? final.valid_until : null, reassessment_at: final ? final.reassessment_at : null, publication_allowed: item.governance_workflow ? !!item.governance_workflow.publication_allowed : false }
    };
    snapshot.snapshot_sha256 = engine.digest(snapshot); return snapshot;
  }
  function compareLocalSnapshots(previous, current) {
    const beforeClaims = new Map(previous.claims.map(function (claim) { return [claim.claim_id, claim]; })); const afterClaims = new Map(current.claims.map(function (claim) { return [claim.claim_id, claim]; })); const wording = [];
    new Set(Array.from(beforeClaims.keys()).concat(Array.from(afterClaims.keys()))).forEach(function (claimId) { const before = beforeClaims.get(claimId); const after = afterClaims.get(claimId); if (!before) wording.push({ claim_id: claimId, change_type: 'added', from_text: null, to_text: after.text, similarity: 0 }); else if (!after) wording.push({ claim_id: claimId, change_type: 'removed', from_text: before.text, to_text: null, similarity: 0 }); else if (before.text !== after.text) wording.push({ claim_id: claimId, change_type: 'modified', from_text: before.text, to_text: after.text, similarity: 0 }); });
    const confidence = []; ['evidence_strength','uncertainty','review_status'].forEach(function (field) { if (previous.confidence_state[field] !== current.confidence_state[field]) confidence.push({ field: field, from: previous.confidence_state[field], to: current.confidence_state[field] }); });
    const addedEvidence = current.evidence_ids.filter(function (id) { return !previous.evidence_ids.includes(id); }); const removedEvidence = previous.evidence_ids.filter(function (id) { return !current.evidence_ids.includes(id); });
    const scoreDelta = current.risk_score - previous.risk_score; const riskLevelChanged = current.risk_level !== previous.risk_level; const materiality = Math.min(100, Math.abs(scoreDelta) * 2 + wording.length * 20 + confidence.length * 15 + addedEvidence.length * 10 + (riskLevelChanged ? 25 : 0)); const severity = materiality >= 70 ? 'critical' : materiality >= 45 ? 'high' : materiality >= 20 ? 'medium' : materiality ? 'low' : 'info'; const reasons = []; if (scoreDelta) reasons.push('Risk score changed by ' + scoreDelta + '.'); if (wording.length) reasons.push(wording.length + ' claim wording change(s) detected.'); if (confidence.length) reasons.push(confidence.length + ' confidence-state change(s) detected.'); if (addedEvidence.length) reasons.push(addedEvidence.length + ' new evidence item(s) detected.');
    const comparison = { comparison_id: uuid(), comparison_version: '1.9.0', case_id: current.case_id, from_snapshot_id: previous.snapshot_id, to_snapshot_id: current.snapshot_id, compared_at: current.captured_at, score_delta: scoreDelta, risk_level_changed: riskLevelChanged, wording_changes: wording, confidence_changes: confidence, evidence_changes: { added_source_ids: current.source_ids.filter(function (id) { return !previous.source_ids.includes(id); }), removed_source_ids: previous.source_ids.filter(function (id) { return !current.source_ids.includes(id); }), added_evidence_ids: addedEvidence, removed_evidence_ids: removedEvidence, content_changed_source_ids: [] }, narrative_changes: { added_node_ids: [], removed_node_ids: [], modified_node_ids: [], added_link_ids: [], removed_link_ids: [] }, freshness_changes: [], governance_changes: [], materiality_score: materiality, severity: severity, material_change: materiality >= 20, reasons: reasons };
    comparison.comparison_sha256 = engine.digest(comparison); return comparison;
  }
  function renderMonitoring(root, item) {
    const summary = root.querySelector('[data-cnrisk-monitoring-summary]'); const detail = root.querySelector('[data-cnrisk-monitoring-detail]'); if (!summary || !detail) return;
    summary.textContent = item.monitoring_snapshots.length + ' snapshot(s) · ' + item.watchlists.filter(function (watch) { return watch.status === 'active'; }).length + ' active watch(es) · ' + item.monitoring_alerts.filter(function (alert) { return alert.status === 'open'; }).length + ' open alert(s).';
    detail.innerHTML = ''; item.monitoring_alerts.slice().reverse().forEach(function (alert) { const row = document.createElement('div'); row.className = 'cnrisk-workspace__governance-item'; row.textContent = alert.severity.toUpperCase() + ' · ' + alert.title + ' · ' + alert.status; detail.appendChild(row); });
  }
  function captureSnapshot(root, runWatch) {
    const id = root.dataset.currentCaseId; if (!id) throw new Error('Open a case first.'); const state = load(); const item = state.cases[id]; const previous = item.monitoring_snapshots.length ? item.monitoring_snapshots[item.monitoring_snapshots.length - 1] : null; const snapshot = monitoringSnapshot(item, runWatch ? 'scheduled' : 'manual'); item.monitoring_snapshots.push(snapshot); addActivity(item, 'monitoring_snapshot_captured', snapshot.snapshot_id, { risk_score: snapshot.risk_score, freshness: snapshot.freshness_report.status }, snapshot.captured_at);
    if (runWatch && previous) { const comparison = compareLocalSnapshots(previous, snapshot); item.monitoring_comparisons.push(comparison); addActivity(item, 'monitoring_snapshots_compared', comparison.comparison_id, { materiality_score: comparison.materiality_score, severity: comparison.severity }, comparison.compared_at); if (comparison.material_change) { const alert = { alert_id: uuid(), alert_version: '1.9.0', case_id: id, watch_id: item.watchlists.length ? item.watchlists[0].watch_id : null, snapshot_id: snapshot.snapshot_id, comparison_id: comparison.comparison_id, alert_type: 'material_change', severity: comparison.severity, title: 'Material narrative change detected', body: comparison.reasons.join(' ') || 'The monitored narrative changed materially.', status: 'open', created_at: snapshot.captured_at, acknowledged_at: null, acknowledged_by: null, resolved_at: null, metadata: { materiality_score: comparison.materiality_score } }; item.monitoring_alerts.push(alert); addActivity(item, 'monitoring_alert_created', alert.alert_id, { alert_type: alert.alert_type, severity: alert.severity }, alert.created_at); } }
    refreshCounts(item); save(state); renderMonitoring(root, item); renderList(root);
  }
  function createLocalWatch(root) {
    const id = root.dataset.currentCaseId; if (!id) throw new Error('Open a case first.'); const state = load(); const item = state.cases[id]; const name = root.querySelector('[data-cnrisk-watch-name]').value.trim() || 'Narrative change watch'; const stamp = now(); const watch = { watch_id: uuid(), watch_version: '1.9.0', case_id: id, name: name, status: 'active', cadence: root.querySelector('[data-cnrisk-watch-cadence]').value, trigger_types: ['material_change','new_evidence','source_stale','reassessment_due'], source_ids: [], created_at: stamp, updated_at: stamp, last_checked_at: null, next_check_at: null, created_by: null, notes: 'Browser-local demonstration watch.' }; item.watchlists.push(watch); addActivity(item, 'watchlist_created', watch.watch_id, { name: watch.name, cadence: watch.cadence }, stamp); refreshCounts(item); save(state); renderMonitoring(root, item); renderList(root);
  }
  function stakeholderSummary(item) {
    const weight = { low: 1, medium: 2, high: 3, critical: 4 };
    const conflict = { none: 0, managed: 1, potential: 2, confirmed: 3, unknown: 1 };
    const scores = {}; const names = {}; const flags = [];
    item.stakeholder_actors.forEach(function (actor) { scores[actor.actor_id] = weight[actor.influence] || 2; names[actor.actor_id] = actor.name; });
    item.stakeholder_pressures.forEach(function (pressure) { scores[pressure.actor_id] = (scores[pressure.actor_id] || 0) + (weight[pressure.intensity] || 2); if (['high','critical'].includes(pressure.intensity) && ['active','anticipated'].includes(pressure.status)) flags.push(pressure.intensity + '_pressure:' + pressure.pressure_id); });
    item.stakeholder_incentives.forEach(function (incentive) { scores[incentive.actor_id] = (scores[incentive.actor_id] || 0) + (conflict[incentive.conflict_status] || 0); if (['potential','confirmed'].includes(incentive.conflict_status)) flags.push(incentive.conflict_status + '_conflict:' + incentive.incentive_id); if (!incentive.disclosed && ['high','critical'].includes(incentive.magnitude)) flags.push('undisclosed_incentive:' + incentive.incentive_id); });
    const highHarm = item.stakeholder_consequences.filter(function (entry) { return ['harm','mixed'].includes(entry.direction) && ['high','critical'].includes(entry.severity); }).length; if (highHarm) flags.push('high_consequence_exposure:' + highHarm);
    const ranking = Object.keys(scores).map(function (actorId) { const actor = item.stakeholder_actors.find(function (entry) { return entry.actor_id === actorId; }) || {}; return { actor_id: actorId, name: names[actorId] || actorId, score: scores[actorId], influence: actor.influence || 'medium', stance: actor.stance || 'unknown' }; }).sort(function (a,b) { return b.score-a.score || a.name.localeCompare(b.name); });
    const maximum = ranking.length ? ranking[0].score : 0; const suggested = maximum <= 3 ? 'low' : maximum <= 5 ? 'medium' : 'high';
    const result = { intelligence_version: '1.9.0', case_id: item.case.case_id, generated_at: item.case.updated_at || now(), counts: { actors: item.stakeholder_actors.length, relationships: item.stakeholder_relationships.length, incentives: item.stakeholder_incentives.length, pressures: item.stakeholder_pressures.length, consequences: item.stakeholder_consequences.length }, suggested_stakeholder_pressure: suggested, maximum_actor_pressure_score: maximum, flags: Array.from(new Set(flags)).sort(), actor_pressure_ranking: ranking, boundary: 'Advisory evidence-linked assessment; does not infer motives or change the canonical score automatically.' };
    result.intelligence_sha256 = engine.digest(result); return result;
  }
  function actorOptions(root, item) {
    root.querySelectorAll('[data-cnrisk-actor-select]').forEach(function (select) { const current=select.value; select.innerHTML='<option value="">Select stakeholder</option>'; item.stakeholder_actors.forEach(function(actor){ const option=document.createElement('option'); option.value=actor.actor_id; option.textContent=actor.name; select.appendChild(option); }); if (current) select.value=current; });
  }
  function renderStakeholders(root, item) {
    const summaryNode=root.querySelector('[data-cnrisk-stakeholder-summary]'); const detail=root.querySelector('[data-cnrisk-stakeholder-detail]'); if(!summaryNode||!detail)return;
    const summary=stakeholderSummary(item); summaryNode.textContent=summary.counts.actors+' actor(s) · '+summary.counts.relationships+' relationship(s) · '+summary.counts.incentives+' incentive(s) · '+summary.counts.pressures+' pressure(s) · suggested pressure '+summary.suggested_stakeholder_pressure+'.';
    detail.innerHTML=''; summary.actor_pressure_ranking.forEach(function(entry){ const row=document.createElement('div'); row.className='cnrisk-workspace__governance-item'; row.textContent=entry.name+' · pressure score '+entry.score+' · '+entry.influence+' influence · '+entry.stance; detail.appendChild(row); });
    summary.flags.forEach(function(flag){ const row=document.createElement('div'); row.className='cnrisk-workspace__governance-item'; row.textContent='Flag · '+flag.replaceAll('_',' '); detail.appendChild(row); }); actorOptions(root,item);
  }
  function currentStakeholderItem(root) { const id=root.dataset.currentCaseId; if(!id) throw new Error('Open a case first.'); const state=load(); return { state:state, item:state.cases[id], caseId:id }; }
  function addStakeholderActor(root) { const context=currentStakeholderItem(root); const name=root.querySelector('[data-cnrisk-actor-name]').value.trim(); if(!name) throw new Error('Stakeholder name is required.'); const stamp=now(); const actor={ actor_id:uuid(), case_id:context.caseId, name:name, actor_type:root.querySelector('[data-cnrisk-actor-type]').value, description:root.querySelector('[data-cnrisk-actor-description]').value.trim(), interests:lines(root.querySelector('[data-cnrisk-actor-interests]').value), influence:root.querySelector('[data-cnrisk-actor-influence]').value, stance:root.querySelector('[data-cnrisk-actor-stance]').value, disclosure_status:root.querySelector('[data-cnrisk-actor-disclosure]').value, external_id:null, notes:'', created_at:stamp, created_by:null }; context.item.stakeholder_actors.push(actor); addActivity(context.item,'stakeholder_actor_added',actor.actor_id,{name:name,actor_type:actor.actor_type},stamp); refreshCounts(context.item); save(context.state); renderStakeholders(root,context.item); renderList(root); }
  function addStakeholderRelationship(root) { const c=currentStakeholderItem(root), source=root.querySelector('[data-cnrisk-relationship-source]').value, target=root.querySelector('[data-cnrisk-relationship-target]').value; if(!source||!target||source===target) throw new Error('Select two different stakeholders.'); const stamp=now(), rel={ relationship_id:uuid(), case_id:c.caseId, source_actor_id:source, target_actor_id:target, relationship_type:root.querySelector('[data-cnrisk-relationship-type]').value, direction:'directed', strength:root.querySelector('[data-cnrisk-relationship-strength]').value, description:root.querySelector('[data-cnrisk-relationship-description]').value.trim(), evidence_ids:[], created_at:stamp, created_by:null }; c.item.stakeholder_relationships.push(rel); addActivity(c.item,'stakeholder_relationship_added',rel.relationship_id,{relationship_type:rel.relationship_type},stamp); refreshCounts(c.item); save(c.state); renderStakeholders(root,c.item); }
  function addStakeholderIncentive(root) { const c=currentStakeholderItem(root), actor=root.querySelector('[data-cnrisk-incentive-actor]').value, description=root.querySelector('[data-cnrisk-incentive-description]').value.trim(); if(!actor||!description) throw new Error('Stakeholder and incentive description are required.'); const conflict=root.querySelector('[data-cnrisk-incentive-conflict]').value; if(conflict==='confirmed') throw new Error('Confirmed conflicts require evidence IDs and should be added through the institutional API.'); const stamp=now(), incentive={ incentive_id:uuid(), case_id:c.caseId, actor_id:actor, incentive_type:root.querySelector('[data-cnrisk-incentive-type]').value, description:description, magnitude:root.querySelector('[data-cnrisk-incentive-magnitude]').value, alignment:root.querySelector('[data-cnrisk-incentive-alignment]').value, disclosed:root.querySelector('[data-cnrisk-incentive-disclosed]').checked, conflict_status:conflict, evidence_ids:[], created_at:stamp, created_by:null }; c.item.stakeholder_incentives.push(incentive); addActivity(c.item,'stakeholder_incentive_added',incentive.incentive_id,{incentive_type:incentive.incentive_type},stamp); refreshCounts(c.item); save(c.state); renderStakeholders(root,c.item); renderList(root); }
  function addStakeholderPressure(root) { const c=currentStakeholderItem(root), actor=root.querySelector('[data-cnrisk-pressure-actor]').value, description=root.querySelector('[data-cnrisk-pressure-description]').value.trim(); if(!actor||!description) throw new Error('Stakeholder and pressure description are required.'); const stamp=now(), pressure={ pressure_id:uuid(), case_id:c.caseId, actor_id:actor, source_actor_id:null, pressure_type:root.querySelector('[data-cnrisk-pressure-type]').value, description:description, intensity:root.querySelector('[data-cnrisk-pressure-intensity]').value, time_horizon:root.querySelector('[data-cnrisk-pressure-horizon]').value, status:'active', evidence_ids:[], created_at:stamp, created_by:null }; c.item.stakeholder_pressures.push(pressure); addActivity(c.item,'stakeholder_pressure_added',pressure.pressure_id,{pressure_type:pressure.pressure_type,intensity:pressure.intensity},stamp); refreshCounts(c.item); save(c.state); renderStakeholders(root,c.item); renderList(root); }
  function addStakeholderConsequence(root) { const c=currentStakeholderItem(root), actor=root.querySelector('[data-cnrisk-consequence-actor]').value, description=root.querySelector('[data-cnrisk-consequence-description]').value.trim(); if(!actor||!description) throw new Error('Stakeholder and consequence description are required.'); const stamp=now(), consequence={ consequence_id:uuid(), case_id:c.caseId, actor_id:actor, impact_type:root.querySelector('[data-cnrisk-consequence-type]').value, direction:root.querySelector('[data-cnrisk-consequence-direction]').value, severity:root.querySelector('[data-cnrisk-consequence-severity]').value, description:description, affected_claim_ids:[], mitigation:'', evidence_ids:[], created_at:stamp, created_by:null }; c.item.stakeholder_consequences.push(consequence); addActivity(c.item,'stakeholder_consequence_added',consequence.consequence_id,{impact_type:consequence.impact_type,direction:consequence.direction},stamp); refreshCounts(c.item); save(c.state); renderStakeholders(root,c.item); renderList(root); }
  function comparativePortfolio(item) {
    const scores=item.revisions.map(function(revision){return revision.record.calculations.risk_score;}).concat(item.scenario_results.map(function(result){return result.scenario_record.calculations.risk_score;}));
    const distribution={low:0,moderate:0,high:0,critical:0}; item.revisions.forEach(function(revision){const level=revision.record.interpretation.risk_level; distribution[level]=(distribution[level]||0)+1;});
    const top=[]; item.sensitivity_analyses.forEach(function(analysis){(analysis.drivers||[]).forEach(function(driver){top.push(driver);});}); top.sort(function(a,b){return (b.range||0)-(a.range||0);});
    const portfolio={ portfolio_id:item.comparative_portfolio&&item.comparative_portfolio.portfolio_id||uuid(), case_id:item.case.case_id, generated_at:now(), comparison_count:item.comparison_sets.length, member_count:item.comparison_sets.reduce(function(total,set){return total+set.members.length;},0), scenario_count:item.scenarios.length, evaluated_scenario_count:item.scenario_results.length, risk_distribution:distribution, scenario_score_range:scores.length?{minimum:Math.min.apply(null,scores),maximum:Math.max.apply(null,scores),range:Math.max.apply(null,scores)-Math.min.apply(null,scores)}:null, top_drivers:top.slice(0,5), publication_readiness:item.governance_workflow?(item.governance_workflow.publication_allowed?'conditional':'blocked'):'not_assessed' };
    portfolio.portfolio_sha256=engine.digest(portfolio); return portfolio;
  }
  function currentComparativeItem(root){const id=root.dataset.currentCaseId;if(!id)throw new Error('Open a case first.');const state=load();const item=state.cases[id];normalizeCaseItem(item);return{state:state,item:item,caseId:id};}
  function scenarioPayload(record,overrides){const n=record.normalized_input;return Object.assign({claim:n.claim,source_type:n.source_type,evidence_strength:n.evidence_strength,uncertainty:n.uncertainty,narrative_volatility:n.narrative_volatility,stakeholder_pressure:n.stakeholder_pressure,time_sensitivity:n.time_sensitivity,consequences:n.consequences,review_status:n.review_status,source_count:n.source_count,method_notes:n.method_notes||''},overrides||{});}
  function buildLocalMatrix(item,comparison){const claims={};comparison.members.forEach(function(member){const revision=item.revisions.find(function(r){return r.record_id===member.record_id;});(revision.record.evidence_ledger.claims||[]).forEach(function(claim){const key=claim.text.toLowerCase().replace(/\s+/g,' ').trim();if(!claims[key])claims[key]={claim_key:key,text:claim.text,member_cells:[]};const coverage=(revision.record.evidence_ledger.coverage.per_claim||[]).find(function(c){return c.claim_id===claim.claim_id;})||{};claims[key].member_cells.push({member_id:member.member_id,claim_ids:[claim.claim_id],coverage_status:coverage.contested?'contested':(coverage.coverage_status||'none'),relationship_counts:coverage.relationship_counts||{support:0,qualify:0,contradict:0,contextualize:0,unresolved:0},source_count:coverage.source_count||0,independent_source_count:coverage.independent_source_count||0,contradiction_count:(coverage.relationship_counts&&coverage.relationship_counts.contradict)||0});});});const rows=Object.values(claims);const matrix={matrix_id:uuid(),matrix_version:'1.9.0',comparison_id:comparison.comparison_id,case_id:item.case.case_id,generated_at:now(),claims:rows,coverage_by_member:comparison.members.map(function(member){return{member_id:member.member_id,covered_claims:rows.filter(function(row){return row.member_cells.some(function(cell){return cell.member_id===member.member_id&&cell.coverage_status!=='none';});}).length,contested_claims:rows.filter(function(row){return row.member_cells.some(function(cell){return cell.member_id===member.member_id&&cell.coverage_status==='contested';});}).length,source_count:0};}),summary:{member_count:comparison.members.length,claim_count:rows.length,divergence_count:rows.filter(function(row){return row.member_cells.length!==comparison.members.length||new Set(row.member_cells.map(function(c){return c.coverage_status;})).size>1;}).length}};matrix.matrix_sha256=engine.digest(matrix);return matrix;}
  function createLocalComparison(root){const c=currentComparativeItem(root);if(c.item.revisions.length<2)throw new Error('Save at least two revisions before creating a comparison.');const revisions=c.item.revisions.slice(-2),stamp=now(),members=revisions.map(function(revision,index){return{member_id:uuid(),label:index?'Alternative revision':'Baseline revision',revision_id:revision.revision_id,record_id:revision.record_id,frame:index?'Competing frame':'Baseline frame',assumptions:[],tags:[],selected:true,added_at:stamp};});const comparison={comparison_id:uuid(),case_id:c.caseId,title:root.querySelector('[data-cnrisk-comparison-title]').value.trim()||'Comparative narrative review',description:'Browser-local comparison of immutable revisions.',status:'active',comparison_mode:'revision',baseline_member_id:members[0].member_id,members:members,created_at:stamp,updated_at:stamp,created_by:null};c.item.comparison_sets.push(comparison);c.item.comparative_evidence_matrices.push(buildLocalMatrix(c.item,comparison));addActivity(c.item,'comparison_set_created',comparison.comparison_id,{member_count:members.length},stamp);refreshCounts(c.item);save(c.state);renderComparative(root,c.item);renderList(root);}
  function addLocalScenario(root){const c=currentComparativeItem(root),comparison=c.item.comparison_sets[c.item.comparison_sets.length-1];if(!comparison)throw new Error('Create a comparison first.');const type=root.querySelector('[data-cnrisk-scenario-type]').value,name=root.querySelector('[data-cnrisk-scenario-name]').value.trim()||type.replaceAll('_',' '),baselineMember=comparison.members.find(function(m){return m.member_id===comparison.baseline_member_id;}),revision=c.item.revisions.find(function(r){return r.record_id===baselineMember.record_id;});let overrides={};if(type==='best_case')overrides={uncertainty:'low',evidence_strength:'strong',consequences:'minor'};else if(type==='worst_case'||type==='adversarial')overrides={uncertainty:'high',evidence_strength:'weak',narrative_volatility:'high',stakeholder_pressure:'high',consequences:'critical'};else if(type==='counterfactual')overrides={source_count:0,evidence_strength:'unclear',uncertainty:'high'};else overrides={uncertainty:'medium'};const stamp=now(),scenario={scenario_id:uuid(),scenario_version:'1.9.0',comparison_id:comparison.comparison_id,case_id:c.caseId,name:name,scenario_type:type,description:'Browser-local explicit scenario override.',assumptions:lines(root.querySelector('[data-cnrisk-scenario-assumptions]').value),parameter_overrides:overrides,evidence_adjustments:[],status:'evaluated',created_at:stamp,updated_at:stamp,created_by:null};const scenarioRecord=engine.buildNarrativeRiskRecord(scenarioPayload(revision.record,overrides),{case_id:c.caseId});const result={result_id:uuid(),result_version:'1.9.0',scenario_id:scenario.scenario_id,comparison_id:comparison.comparison_id,case_id:c.caseId,baseline_member_id:comparison.baseline_member_id,generated_at:stamp,baseline_record_id:revision.record_id,baseline_score:revision.record.calculations.risk_score,baseline_risk_level:revision.record.interpretation.risk_level,scenario_record:scenarioRecord,deltas:{risk_score:scenarioRecord.calculations.risk_score-revision.record.calculations.risk_score,risk_level_changed:scenarioRecord.interpretation.risk_level!==revision.record.interpretation.risk_level},advisory_findings:['Scenario output reflects explicit assumptions and does not replace the canonical record.']};result.result_sha256=engine.digest(result);c.item.scenarios.push(scenario);c.item.scenario_results.push(result);addActivity(c.item,'scenario_evaluated',scenario.scenario_id,{scenario_type:type,risk_score_delta:result.deltas.risk_score},stamp);refreshCounts(c.item);save(c.state);renderComparative(root,c.item);renderList(root);}
  function runLocalSensitivity(root){const c=currentComparativeItem(root),comparison=c.item.comparison_sets[c.item.comparison_sets.length-1];if(!comparison)throw new Error('Create a comparison first.');const baseline=comparison.members.find(function(m){return m.member_id===comparison.baseline_member_id;}),revision=c.item.revisions.find(function(r){return r.record_id===baseline.record_id;}),values=['low','medium','high'],runs=values.map(function(value){const record=engine.buildNarrativeRiskRecord(scenarioPayload(revision.record,{uncertainty:value}),{case_id:c.caseId});return{dimension:'uncertainty',value:value,risk_score:record.calculations.risk_score,risk_level:record.interpretation.risk_level};}),scores=runs.map(function(r){return r.risk_score;}),stamp=now(),analysis={analysis_id:uuid(),analysis_version:'1.9.0',comparison_id:comparison.comparison_id,case_id:c.caseId,baseline_member_id:comparison.baseline_member_id,generated_at:stamp,dimensions:['uncertainty'],runs:runs,drivers:[{dimension:'uncertainty',minimum:Math.min.apply(null,scores),maximum:Math.max.apply(null,scores),range:Math.max.apply(null,scores)-Math.min.apply(null,scores),most_sensitive_value:runs.slice().sort(function(a,b){return b.risk_score-a.risk_score;})[0].value}],advisory_findings:['Sensitivity ranges are advisory and depend on the declared method snapshot.']};analysis.analysis_sha256=engine.digest(analysis);c.item.sensitivity_analyses.push(analysis);addActivity(c.item,'sensitivity_analysis_completed',analysis.analysis_id,{dimensions:analysis.dimensions},stamp);refreshCounts(c.item);save(c.state);renderComparative(root,c.item);}
  function createLocalDecisionStudioHandoff(root){const c=currentComparativeItem(root),comparison=c.item.comparison_sets[c.item.comparison_sets.length-1];if(!comparison)throw new Error('Create a comparison first.');const stamp=now(),handoff={handoff_id:uuid(),handoff_version:'1.9.0',handoff_type:'catalyst_narrative_risk_decision_studio_handoff',case_id:c.caseId,comparison_id:comparison.comparison_id,generated_at:stamp,comparison_set:comparison,evidence_matrix:c.item.comparative_evidence_matrices.filter(function(m){return m.comparison_id===comparison.comparison_id;}).slice(-1)[0]||null,scenarios:c.item.scenarios.filter(function(x){return x.comparison_id===comparison.comparison_id;}),selected_scenario_ids:c.item.scenarios.filter(function(x){return x.comparison_id===comparison.comparison_id;}).map(function(x){return x.scenario_id;}),scenario_results:c.item.scenario_results.filter(function(x){return x.comparison_id===comparison.comparison_id;}),sensitivity_analyses:c.item.sensitivity_analyses.filter(function(x){return x.comparison_id===comparison.comparison_id;}),governance_summary:{workflow_status:c.item.case.workflow_status,final_disposition:c.item.case.final_disposition,publication_allowed:c.item.case.publication_allowed},advisory_boundary:'Decision Studio receives explicit comparative artifacts; it must not treat them as truth certification or automatic selection.'};handoff.handoff_sha256=engine.digest(handoff);c.item.decision_studio_handoffs.push(handoff);addActivity(c.item,'decision_studio_handoff_created',handoff.handoff_id,{comparison_id:comparison.comparison_id},stamp);refreshCounts(c.item);save(c.state);renderComparative(root,c.item);download('narrative-risk-decision-studio-handoff-v1.9.0.json',handoff);}
  function renderComparative(root,item){const summary=root.querySelector('[data-cnrisk-comparative-summary]'),detail=root.querySelector('[data-cnrisk-comparative-detail]');if(!summary||!detail)return;refreshCounts(item);summary.textContent=item.comparison_sets.length+' comparison set(s) · '+item.scenario_results.length+' evaluated scenario(s) · '+item.sensitivity_analyses.length+' sensitivity analysis(es) · '+item.decision_studio_handoffs.length+' Decision Studio handoff(s)';detail.innerHTML='';item.comparison_sets.forEach(function(comparison){const block=document.createElement('div');block.className='cnrisk-workspace__governance-item';block.textContent=comparison.title+' · '+comparison.members.length+' narratives · '+comparison.status;detail.appendChild(block);});item.scenario_results.slice(-5).forEach(function(result){const block=document.createElement('div');block.className='cnrisk-workspace__governance-item';const scenario=item.scenarios.find(function(x){return x.scenario_id===result.scenario_id;});block.textContent=(scenario?scenario.name:'Scenario')+' · score '+result.scenario_record.calculations.risk_score+' · delta '+result.deltas.risk_score;detail.appendChild(block);});}
  function importBundle(root, file) {
    const reader = new FileReader(); reader.onload = function () {
      try {
        const data = JSON.parse(reader.result); if (data.bundle_type !== 'catalyst_narrative_risk_case_bundle' || data.bundle_version !== '1.9.0') throw new Error('Not a v1.9.0 narrative-risk case bundle.');
        const expected = data.bundle_sha256; const unsigned = Object.assign({}, data); delete unsigned.bundle_sha256; if (engine.digest(unsigned) !== expected) throw new Error('Bundle checksum does not match.');
        const state = load(); const caseId = data.case.case_id; if (state.cases[caseId]) throw new Error('A case with this identifier already exists.');
        state.cases[caseId] = { case: data.case, revisions: data.revisions, review_events: data.review_events, activity: data.activity, governance_workflow: data.governance_workflow, review_assignments: data.review_assignments, governance_decisions: data.governance_decisions, monitoring_snapshots: data.monitoring_snapshots, monitoring_comparisons: data.monitoring_comparisons, watchlists: data.watchlists, monitoring_alerts: data.monitoring_alerts, site_intelligence_events: data.site_intelligence_events, stakeholder_actors: data.stakeholder_actors, stakeholder_relationships: data.stakeholder_relationships, stakeholder_incentives: data.stakeholder_incentives, stakeholder_pressures: data.stakeholder_pressures, stakeholder_consequences: data.stakeholder_consequences, catalyst_canvas_handoffs: data.catalyst_canvas_handoffs, comparison_sets: data.comparison_sets, comparative_evidence_matrices: data.comparative_evidence_matrices, scenarios: data.scenarios, scenario_results: data.scenario_results, sensitivity_analyses: data.sensitivity_analyses, comparative_portfolio: data.comparative_portfolio, decision_studio_handoffs: data.decision_studio_handoffs, publication_briefings: data.publication_briefings, publication_packages: data.publication_packages, public_embeds: data.public_embeds, platform_handoffs: data.platform_handoffs }; normalizeCaseItem(state.cases[caseId]); save(state); renderList(root); openCase(root, caseId);
      } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; }
    }; reader.readAsText(file);
  }
  function guarded(root, callback, success) { try { callback(); root.querySelector('[data-cnrisk-workspace-message]').textContent = success || ''; } catch (error) { root.querySelector('[data-cnrisk-workspace-message]').textContent = error.message; } }
  function init(root) {
    const form = root.querySelector('[data-cnrisk-workspace-form]');
    form.addEventListener('submit', function (event) { event.preventDefault(); guarded(root, function () { createOrRevise(root, form); }, 'Case revision saved in this browser.'); });
    root.querySelector('[data-cnrisk-new-case]').addEventListener('click', function () { delete root.dataset.currentCaseId; form.reset(); root.querySelector('[data-cnrisk-workspace-detail]').innerHTML = '<p>Start a new case or open an existing one.</p>'; root.querySelector('[data-cnrisk-governance-summary]').textContent = 'No governance workflow started.'; root.querySelector('[data-cnrisk-governance-assignments]').innerHTML = ''; root.querySelector('[data-cnrisk-governance-decisions]').innerHTML = ''; root.querySelector('[data-cnrisk-comparative-summary]').textContent = 'No comparison set created.'; root.querySelector('[data-cnrisk-comparative-detail]').innerHTML = ''; });
    root.querySelector('[data-cnrisk-workspace-search]').addEventListener('input', function () { renderList(root); });
    root.querySelector('[data-cnrisk-add-review]').addEventListener('click', function () { guarded(root, function () { addReview(root); }, 'Review activity saved.'); });
    root.querySelector('[data-cnrisk-start-governance]').addEventListener('click', function () { guarded(root, function () { startGovernance(root); }, 'Governance workflow started.'); });
    root.querySelector('[data-cnrisk-assign-reviewer]').addEventListener('click', function () { guarded(root, function () { assignReviewer(root); }, 'Reviewer assigned.'); });
    root.querySelector('[data-cnrisk-add-decision]').addEventListener('click', function () { guarded(root, function () { addDecision(root); }, 'Governance decision recorded.'); });
    root.querySelector('[data-cnrisk-capture-snapshot]').addEventListener('click', function () { guarded(root, function () { captureSnapshot(root, false); }, 'Monitoring snapshot captured.'); });
    root.querySelector('[data-cnrisk-create-watch]').addEventListener('click', function () { guarded(root, function () { createLocalWatch(root); }, 'Monitoring watch created.'); });
    root.querySelector('[data-cnrisk-run-watch]').addEventListener('click', function () { guarded(root, function () { captureSnapshot(root, true); }, 'Monitoring check completed.'); });
    root.querySelector('[data-cnrisk-add-actor]').addEventListener('click', function () { guarded(root, function () { addStakeholderActor(root); }, 'Stakeholder added.'); });
    root.querySelector('[data-cnrisk-add-relationship]').addEventListener('click', function () { guarded(root, function () { addStakeholderRelationship(root); }, 'Stakeholder relationship added.'); });
    root.querySelector('[data-cnrisk-add-incentive]').addEventListener('click', function () { guarded(root, function () { addStakeholderIncentive(root); }, 'Stakeholder incentive added.'); });
    root.querySelector('[data-cnrisk-add-pressure]').addEventListener('click', function () { guarded(root, function () { addStakeholderPressure(root); }, 'Stakeholder pressure added.'); });
    root.querySelector('[data-cnrisk-add-consequence]').addEventListener('click', function () { guarded(root, function () { addStakeholderConsequence(root); }, 'Stakeholder consequence added.'); });
    root.querySelector('[data-cnrisk-create-comparison]').addEventListener('click', function () { guarded(root, function () { createLocalComparison(root); }, 'Comparative narrative set created.'); });
    root.querySelector('[data-cnrisk-add-scenario]').addEventListener('click', function () { guarded(root, function () { addLocalScenario(root); }, 'Scenario evaluated.'); });
    root.querySelector('[data-cnrisk-run-sensitivity]').addEventListener('click', function () { guarded(root, function () { runLocalSensitivity(root); }, 'Sensitivity analysis completed.'); });
    root.querySelector('[data-cnrisk-decision-studio-handoff]').addEventListener('click', function () { guarded(root, function () { createLocalDecisionStudioHandoff(root); }, 'Decision Studio handoff created.'); });
    root.querySelector('[data-cnrisk-assignment-stage]').addEventListener('change', function () { root.querySelector('[data-cnrisk-reviewer-role]').value = ROLE_BY_STAGE[this.value]; root.querySelector('[data-cnrisk-decision-stage]').value = this.value; });
    root.querySelector('[data-cnrisk-archive-case]').addEventListener('click', function () { const id = root.dataset.currentCaseId; if (!id) return; const state = load(); const item = state.cases[id]; item.case.archived = true; item.case.archived_at = now(); addActivity(item, 'case_archived', id, {}); refreshCounts(item); save(state); delete root.dataset.currentCaseId; renderList(root); });
    root.querySelector('[data-cnrisk-import-bundle]').addEventListener('change', function () { if (this.files[0]) importBundle(root, this.files[0]); this.value = ''; });
    renderList(root);
  }
  document.addEventListener('DOMContentLoaded', function () { document.querySelectorAll('[data-cnrisk-workspace]').forEach(init); });
})();
