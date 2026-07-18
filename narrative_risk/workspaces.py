"""SQLite-backed persistent cases, revisions, review events, and portable bundles.

The workspace layer treats canonical narrative-risk records as immutable revision
artifacts. Case metadata may change, while revisions and activity entries are
append-only. This module uses only Python's standard-library sqlite3 driver so
local and institutional deployments share the same repository contract.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Sequence
from uuid import UUID, uuid4

from .contracts import (
    CASE_SCHEMA_PATH,
    REVISION_SCHEMA_PATH,
    REVIEW_EVENT_SCHEMA_PATH,
    SAVED_VIEW_SCHEMA_PATH,
    WORKSPACE_BUNDLE_SCHEMA_PATH,
    REVIEW_ASSIGNMENT_SCHEMA_PATH,
    GOVERNANCE_WORKFLOW_SCHEMA_PATH,
    GOVERNANCE_DECISION_SCHEMA_PATH,
    REVIEW_TEMPLATE_SCHEMA_PATH,
    MONITORING_SNAPSHOT_SCHEMA_PATH, MONITORING_COMPARISON_SCHEMA_PATH,
    WATCHLIST_SCHEMA_PATH, MONITORING_ALERT_SCHEMA_PATH,
    COMPARISON_SET_SCHEMA_PATH, COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH,
    SCENARIO_SCHEMA_PATH, SCENARIO_RESULT_SCHEMA_PATH, SENSITIVITY_ANALYSIS_SCHEMA_PATH,
    COMPARATIVE_PORTFOLIO_SCHEMA_PATH, DECISION_STUDIO_HANDOFF_SCHEMA_PATH,
    BRIEFING_SCHEMA_PATH, PUBLICATION_PACKAGE_SCHEMA_PATH, PUBLIC_EMBED_SCHEMA_PATH,
    API_KEY_SCHEMA_PATH, PLATFORM_HANDOFF_SCHEMA_PATH,
    PRIVACY_POLICY_SCHEMA_PATH, RETENTION_ASSESSMENT_SCHEMA_PATH, BACKUP_MANIFEST_SCHEMA_PATH,
    canonical_json,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError
from .governance import (
    ASSIGNMENT_STATUSES, GOVERNANCE_DISPOSITIONS, GOVERNANCE_ROLES, PUBLICATION_RESTRICTIONS,
    REVIEWER_ROLES, REVIEW_STAGES, WORKFLOW_STATUSES, default_template_payload, is_past,
    normalize_string_list, normalize_template_stages, require_permission,
)
from .service import build_narrative_risk_record, validate_narrative_risk_record
from .monitoring import (
    ALERT_SEVERITIES, ALERT_STATUSES, ALERT_TYPES, WATCH_CADENCES, WATCH_STATUSES, WATCH_TRIGGERS,
    build_alert, build_monitoring_snapshot, compare_monitoring_snapshots, normalize_watchlist,
    validate_site_intelligence_handoff, validate_datetime as monitoring_datetime, urn_uuid as monitoring_urn_uuid,
)
from .stakeholders import (
    build_stakeholder_intelligence, normalize_actor, normalize_relationship, normalize_incentive,
    normalize_pressure, normalize_consequence, validate_canvas_handoff,
)
from .publication import (
    build_briefing, build_publication_package, build_public_embed, create_api_key_record,
    authorize_api_key, build_platform_handoff, urn as publication_urn,
)
from .hardening import (
    normalize_privacy_policy, build_retention_assessment, create_sqlite_backup,
    verify_sqlite_backup, restore_sqlite_backup, build_performance_report,
)
from .comparisons import (
    normalize_comparison_set, build_evidence_matrix, normalize_scenario, evaluate_scenario,
    run_sensitivity_analysis, build_comparative_portfolio, build_decision_studio_handoff,
    urn as comparison_urn,
)
from .connected import (
    build_connected_dossier, build_institutional_workspace, build_integration_route,
    normalize_platform_event,
)

VERSION = "2.0.0"
BUNDLE_TYPE = "catalyst_narrative_risk_case_bundle"
CASE_STATUSES = {"draft", "active", "in_review", "approved", "closed"}
CASE_PRIORITIES = {"low", "normal", "high", "critical"}
REVIEW_EVENT_TYPES = {
    "comment", "review_requested", "review_completed", "decision_updated",
    "status_changed", "assignment_changed", "workflow_started", "stage_decision",
    "approval_expired", "reassessment_due", "monitoring_snapshot", "monitoring_alert", "source_change",
}
SAVED_VIEW_FIELDS = {"query", "organization_id", "project_id", "status", "priority", "tags", "archived"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_datetime(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string") from exc
    if parsed.tzinfo is None:
        raise NarrativeRiskValidationError(f"{field} must include a timezone")
    return value


def _urn_uuid(value: str | None, field: str) -> str:
    if value is None:
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except (ValueError, AttributeError) as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def _text(value: Any, field: str, *, required: bool = False, maximum: int = 20000) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if required and not cleaned:
        raise NarrativeRiskValidationError(f"{field} is required")
    if len(cleaned) > maximum:
        raise NarrativeRiskValidationError(f"{field} must be no longer than {maximum} characters")
    return cleaned


def _nullable_text(value: Any, field: str, *, maximum: int = 500) -> str | None:
    if value is None or value == "":
        return None
    return _text(value, field, maximum=maximum)


def _choice(value: Any, field: str, allowed: Iterable[str], default: str) -> str:
    if value is None or value == "":
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    allowed_values = sorted(allowed)
    if cleaned not in allowed_values:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(allowed_values)}")
    return cleaned


def _tags(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NarrativeRiskValidationError("tags must be an array of strings")
    output: List[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        tag = _text(raw, f"tags[{index}]", required=True, maximum=100)
        key = tag.casefold()
        if key not in seen:
            output.append(tag)
            seen.add(key)
    if len(output) > 100:
        raise NarrativeRiskValidationError("tags must contain no more than 100 values")
    return output


def _json_load(value: str) -> Any:
    return json.loads(value)


def _json_dump(value: Any) -> str:
    return canonical_json(value)


def _schema_error(label: str, value: Mapping[str, Any], schema_path: Path) -> None:
    try:
        validate_against_schema(value, schema_path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


class SQLiteCaseRepository:
    """Persistent repository for cases and immutable narrative-risk revisions."""

    def __init__(self, database_path: str | Path = ":memory:") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")
        self.initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS workspace_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            organization_id TEXT,
            project_id TEXT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]',
            archived_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            current_revision INTEGER NOT NULL DEFAULT 0,
            latest_record_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
        CREATE INDEX IF NOT EXISTS idx_cases_priority ON cases(priority);
        CREATE INDEX IF NOT EXISTS idx_cases_org_project ON cases(organization_id, project_id);
        CREATE INDEX IF NOT EXISTS idx_cases_updated ON cases(updated_at DESC);

        CREATE TABLE IF NOT EXISTS revisions (
            revision_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_number INTEGER NOT NULL,
            record_id TEXT NOT NULL UNIQUE,
            record_json TEXT NOT NULL,
            record_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT,
            change_note TEXT NOT NULL DEFAULT '',
            UNIQUE(case_id, revision_number)
        );
        CREATE INDEX IF NOT EXISTS idx_revisions_case ON revisions(case_id, revision_number DESC);

        CREATE TABLE IF NOT EXISTS review_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_id TEXT REFERENCES revisions(revision_id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            author_id TEXT,
            author_name TEXT,
            body TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_review_events_case ON review_events(case_id, created_at);

        CREATE TABLE IF NOT EXISTS review_templates (
            template_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            stages_json TEXT NOT NULL,
            default_due_days INTEGER NOT NULL DEFAULT 14,
            escalation_days INTEGER NOT NULL DEFAULT 3,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_review_templates_active ON review_templates(active, name);

        CREATE TABLE IF NOT EXISTS governance_workflows (
            workflow_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL UNIQUE REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
            template_id TEXT,
            template_snapshot_json TEXT NOT NULL,
            status TEXT NOT NULL,
            current_stage TEXT NOT NULL,
            started_at TEXT NOT NULL,
            due_at TEXT,
            completed_at TEXT,
            created_by TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_governance_workflows_status ON governance_workflows(status, current_stage);
        CREATE INDEX IF NOT EXISTS idx_governance_workflows_due ON governance_workflows(due_at);

        CREATE TABLE IF NOT EXISTS review_assignments (
            assignment_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
            workflow_id TEXT NOT NULL REFERENCES governance_workflows(workflow_id) ON DELETE RESTRICT,
            stage TEXT NOT NULL,
            reviewer_id TEXT NOT NULL,
            reviewer_name TEXT,
            reviewer_role TEXT NOT NULL,
            status TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 1,
            instructions TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            created_by TEXT,
            due_at TEXT,
            accepted_at TEXT,
            completed_at TEXT,
            escalated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_review_assignments_queue ON review_assignments(reviewer_id, status, due_at);
        CREATE INDEX IF NOT EXISTS idx_review_assignments_case ON review_assignments(case_id, stage, status);

        CREATE TABLE IF NOT EXISTS governance_decisions (
            decision_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
            workflow_id TEXT NOT NULL REFERENCES governance_workflows(workflow_id) ON DELETE RESTRICT,
            assignment_id TEXT REFERENCES review_assignments(assignment_id) ON DELETE RESTRICT,
            stage TEXT NOT NULL,
            disposition TEXT NOT NULL,
            decided_by TEXT NOT NULL,
            decided_by_name TEXT,
            decider_role TEXT NOT NULL,
            decided_at TEXT NOT NULL,
            rationale TEXT NOT NULL,
            conditions_json TEXT NOT NULL DEFAULT '[]',
            required_wording_json TEXT NOT NULL DEFAULT '[]',
            publication_restrictions_json TEXT NOT NULL DEFAULT '[]',
            disclosures_json TEXT NOT NULL DEFAULT '[]',
            valid_until TEXT,
            reassessment_at TEXT,
            supersedes_decision_id TEXT REFERENCES governance_decisions(decision_id) ON DELETE RESTRICT
        );
        CREATE INDEX IF NOT EXISTS idx_governance_decisions_case ON governance_decisions(case_id, stage, decided_at);
        CREATE TRIGGER IF NOT EXISTS governance_decisions_no_update
        BEFORE UPDATE ON governance_decisions BEGIN SELECT RAISE(ABORT, 'governance decisions are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS governance_decisions_no_delete
        BEFORE DELETE ON governance_decisions BEGIN SELECT RAISE(ABORT, 'governance decisions are append-only'); END;

        CREATE TABLE IF NOT EXISTS monitoring_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_id TEXT REFERENCES revisions(revision_id) ON DELETE RESTRICT,
            record_id TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            trigger TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            snapshot_sha256 TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_monitoring_snapshots_case ON monitoring_snapshots(case_id, captured_at);
        CREATE TRIGGER IF NOT EXISTS monitoring_snapshots_no_update
        BEFORE UPDATE ON monitoring_snapshots BEGIN SELECT RAISE(ABORT, 'monitoring snapshots are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS monitoring_snapshots_no_delete
        BEFORE DELETE ON monitoring_snapshots BEGIN SELECT RAISE(ABORT, 'monitoring snapshots are append-only'); END;

        CREATE TABLE IF NOT EXISTS monitoring_comparisons (
            comparison_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            from_snapshot_id TEXT NOT NULL REFERENCES monitoring_snapshots(snapshot_id) ON DELETE RESTRICT,
            to_snapshot_id TEXT NOT NULL REFERENCES monitoring_snapshots(snapshot_id) ON DELETE RESTRICT,
            compared_at TEXT NOT NULL,
            materiality_score INTEGER NOT NULL,
            severity TEXT NOT NULL,
            comparison_json TEXT NOT NULL,
            comparison_sha256 TEXT NOT NULL,
            UNIQUE(from_snapshot_id, to_snapshot_id)
        );
        CREATE INDEX IF NOT EXISTS idx_monitoring_comparisons_case ON monitoring_comparisons(case_id, compared_at);
        CREATE TRIGGER IF NOT EXISTS monitoring_comparisons_no_update
        BEFORE UPDATE ON monitoring_comparisons BEGIN SELECT RAISE(ABORT, 'monitoring comparisons are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS monitoring_comparisons_no_delete
        BEFORE DELETE ON monitoring_comparisons BEGIN SELECT RAISE(ABORT, 'monitoring comparisons are append-only'); END;

        CREATE TABLE IF NOT EXISTS watchlists (
            watch_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            cadence TEXT NOT NULL,
            trigger_types_json TEXT NOT NULL,
            source_ids_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_checked_at TEXT,
            next_check_at TEXT,
            created_by TEXT,
            notes TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_watchlists_due ON watchlists(status, next_check_at);
        CREATE INDEX IF NOT EXISTS idx_watchlists_case ON watchlists(case_id, status);

        CREATE TABLE IF NOT EXISTS monitoring_alerts (
            alert_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            watch_id TEXT REFERENCES watchlists(watch_id) ON DELETE RESTRICT,
            snapshot_id TEXT REFERENCES monitoring_snapshots(snapshot_id) ON DELETE RESTRICT,
            comparison_id TEXT REFERENCES monitoring_comparisons(comparison_id) ON DELETE RESTRICT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            acknowledged_at TEXT,
            acknowledged_by TEXT,
            resolved_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_queue ON monitoring_alerts(status, severity, created_at);
        CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_case ON monitoring_alerts(case_id, status);

        CREATE TABLE IF NOT EXISTS site_intelligence_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            handoff_json TEXT NOT NULL,
            handoff_sha256 TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_site_intelligence_events_case ON site_intelligence_events(case_id, observed_at);
        CREATE TRIGGER IF NOT EXISTS site_intelligence_events_no_update
        BEFORE UPDATE ON site_intelligence_events BEGIN SELECT RAISE(ABORT, 'site intelligence events are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS site_intelligence_events_no_delete
        BEFORE DELETE ON site_intelligence_events BEGIN SELECT RAISE(ABORT, 'site intelligence events are append-only'); END;

        CREATE TABLE IF NOT EXISTS stakeholder_actors (
            actor_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            actor_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stakeholder_actors_case ON stakeholder_actors(case_id, created_at);
        CREATE TABLE IF NOT EXISTS stakeholder_relationships (
            relationship_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            source_actor_id TEXT NOT NULL REFERENCES stakeholder_actors(actor_id) ON DELETE RESTRICT,
            target_actor_id TEXT NOT NULL REFERENCES stakeholder_actors(actor_id) ON DELETE RESTRICT,
            relationship_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stakeholder_relationships_case ON stakeholder_relationships(case_id, created_at);
        CREATE TABLE IF NOT EXISTS stakeholder_incentives (
            incentive_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            actor_id TEXT NOT NULL REFERENCES stakeholder_actors(actor_id) ON DELETE RESTRICT,
            incentive_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stakeholder_incentives_case ON stakeholder_incentives(case_id, created_at);
        CREATE TABLE IF NOT EXISTS stakeholder_pressures (
            pressure_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            actor_id TEXT NOT NULL REFERENCES stakeholder_actors(actor_id) ON DELETE RESTRICT,
            source_actor_id TEXT REFERENCES stakeholder_actors(actor_id) ON DELETE RESTRICT,
            pressure_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stakeholder_pressures_case ON stakeholder_pressures(case_id, created_at);
        CREATE TABLE IF NOT EXISTS stakeholder_consequences (
            consequence_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            actor_id TEXT NOT NULL REFERENCES stakeholder_actors(actor_id) ON DELETE RESTRICT,
            consequence_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stakeholder_consequences_case ON stakeholder_consequences(case_id, created_at);
        CREATE TABLE IF NOT EXISTS catalyst_canvas_handoffs (
            handoff_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            canvas_id TEXT NOT NULL, handoff_json TEXT NOT NULL, handoff_sha256 TEXT NOT NULL, imported_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_canvas_handoffs_case ON catalyst_canvas_handoffs(case_id, imported_at);

        CREATE TABLE IF NOT EXISTS comparison_sets (
            comparison_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            comparison_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_comparison_sets_case ON comparison_sets(case_id, status, updated_at);
        CREATE TABLE IF NOT EXISTS comparative_evidence_matrices (
            matrix_id TEXT PRIMARY KEY, comparison_id TEXT NOT NULL REFERENCES comparison_sets(comparison_id) ON DELETE RESTRICT,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT, matrix_json TEXT NOT NULL, matrix_sha256 TEXT NOT NULL, generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_comparative_matrices_case ON comparative_evidence_matrices(case_id, generated_at);
        CREATE TABLE IF NOT EXISTS scenarios (
            scenario_id TEXT PRIMARY KEY, comparison_id TEXT NOT NULL REFERENCES comparison_sets(comparison_id) ON DELETE RESTRICT,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT, scenario_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scenarios_comparison ON scenarios(comparison_id, status, updated_at);
        CREATE TABLE IF NOT EXISTS scenario_results (
            result_id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL REFERENCES scenarios(scenario_id) ON DELETE RESTRICT,
            comparison_id TEXT NOT NULL REFERENCES comparison_sets(comparison_id) ON DELETE RESTRICT,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT, result_json TEXT NOT NULL, result_sha256 TEXT NOT NULL, generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scenario_results_comparison ON scenario_results(comparison_id, generated_at);
        CREATE TABLE IF NOT EXISTS sensitivity_analyses (
            analysis_id TEXT PRIMARY KEY, comparison_id TEXT NOT NULL REFERENCES comparison_sets(comparison_id) ON DELETE RESTRICT,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT, analysis_json TEXT NOT NULL, analysis_sha256 TEXT NOT NULL, generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sensitivity_case ON sensitivity_analyses(case_id, generated_at);
        CREATE TABLE IF NOT EXISTS decision_studio_handoffs (
            handoff_id TEXT PRIMARY KEY, comparison_id TEXT NOT NULL REFERENCES comparison_sets(comparison_id) ON DELETE RESTRICT,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT, handoff_json TEXT NOT NULL, handoff_sha256 TEXT NOT NULL, generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_decision_handoffs_case ON decision_studio_handoffs(case_id, generated_at);

        CREATE TABLE IF NOT EXISTS publication_briefings (
            briefing_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
            briefing_json TEXT NOT NULL, briefing_sha256 TEXT NOT NULL, classification TEXT NOT NULL, audience TEXT NOT NULL, generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_publication_briefings_case ON publication_briefings(case_id, generated_at);
        CREATE TABLE IF NOT EXISTS publication_packages (
            package_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            briefing_id TEXT NOT NULL REFERENCES publication_briefings(briefing_id) ON DELETE RESTRICT,
            package_json TEXT NOT NULL, package_sha256 TEXT NOT NULL, status TEXT NOT NULL, slug TEXT NOT NULL,
            package_version INTEGER NOT NULL, idempotency_key TEXT, generated_at TEXT NOT NULL, UNIQUE(case_id, slug, package_version), UNIQUE(idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS idx_publication_packages_case ON publication_packages(case_id, status, generated_at);
        CREATE TABLE IF NOT EXISTS public_embeds (
            embed_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            package_id TEXT NOT NULL REFERENCES publication_packages(package_id) ON DELETE RESTRICT,
            embed_json TEXT NOT NULL, embed_sha256 TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_public_embeds_case ON public_embeds(case_id, status, created_at);
        CREATE TABLE IF NOT EXISTS api_keys (
            api_key_id TEXT PRIMARY KEY, name TEXT NOT NULL, key_prefix TEXT NOT NULL UNIQUE, key_sha256 TEXT NOT NULL UNIQUE,
            scopes_json TEXT NOT NULL, status TEXT NOT NULL, rate_limit_per_minute INTEGER NOT NULL, created_at TEXT NOT NULL,
            expires_at TEXT, last_used_at TEXT, created_by TEXT
        );
        CREATE TABLE IF NOT EXISTS api_key_usage (
            usage_id INTEGER PRIMARY KEY AUTOINCREMENT, api_key_id TEXT NOT NULL REFERENCES api_keys(api_key_id) ON DELETE RESTRICT, used_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_api_key_usage_window ON api_key_usage(api_key_id, used_at);
        CREATE TABLE IF NOT EXISTS platform_handoffs (
            handoff_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            package_id TEXT NOT NULL REFERENCES publication_packages(package_id) ON DELETE RESTRICT,
            target TEXT NOT NULL, handoff_json TEXT NOT NULL, handoff_sha256 TEXT NOT NULL, generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_platform_handoffs_case ON platform_handoffs(case_id, target, generated_at);

        CREATE TABLE IF NOT EXISTS privacy_policies (
            policy_id TEXT PRIMARY KEY,
            policy_json TEXT NOT NULL,
            policy_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_privacy_policies_status ON privacy_policies(status, updated_at);

        CREATE TABLE IF NOT EXISTS retention_assessments (
            assessment_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            policy_id TEXT NOT NULL,
            assessment_json TEXT NOT NULL,
            assessment_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            assessed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_retention_assessments_case ON retention_assessments(case_id, assessed_at);
        CREATE TRIGGER IF NOT EXISTS retention_assessments_no_update
        BEFORE UPDATE ON retention_assessments BEGIN SELECT RAISE(ABORT, 'retention assessments are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS retention_assessments_no_delete
        BEFORE DELETE ON retention_assessments BEGIN SELECT RAISE(ABORT, 'retention assessments are append-only'); END;

        CREATE TABLE IF NOT EXISTS backup_manifests (
            backup_id TEXT PRIMARY KEY,
            manifest_json TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            backup_path TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS connected_dossiers (
            dossier_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            dossier_json TEXT NOT NULL,
            dossier_sha256 TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_connected_dossiers_case ON connected_dossiers(case_id, generated_at);
        CREATE TRIGGER IF NOT EXISTS connected_dossiers_no_update
        BEFORE UPDATE ON connected_dossiers BEGIN SELECT RAISE(ABORT, 'connected dossiers are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS connected_dossiers_no_delete
        BEFORE DELETE ON connected_dossiers BEGIN SELECT RAISE(ABORT, 'connected dossiers are append-only'); END;

        CREATE TABLE IF NOT EXISTS platform_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT REFERENCES cases(case_id) ON DELETE RESTRICT,
            source_module TEXT NOT NULL,
            event_type TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            event_json TEXT NOT NULL,
            event_sha256 TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_platform_events_case ON platform_events(case_id, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_platform_events_source ON platform_events(source_module, event_type);
        CREATE TRIGGER IF NOT EXISTS platform_events_no_update
        BEFORE UPDATE ON platform_events BEGIN SELECT RAISE(ABORT, 'platform events are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS platform_events_no_delete
        BEFORE DELETE ON platform_events BEGIN SELECT RAISE(ABORT, 'platform events are append-only'); END;

        CREATE TABLE IF NOT EXISTS integration_routes (
            route_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            source_module TEXT NOT NULL,
            target_module TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            artifact_id TEXT NOT NULL,
            status TEXT NOT NULL,
            route_json TEXT NOT NULL,
            route_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_integration_routes_case ON integration_routes(case_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_integration_routes_modules ON integration_routes(source_module, target_module, status);

        CREATE TABLE IF NOT EXISTS institutional_workspaces (
            workspace_id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            workspace_json TEXT NOT NULL,
            workspace_sha256 TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_institutional_workspaces_org ON institutional_workspaces(organization_id, generated_at);
        CREATE TRIGGER IF NOT EXISTS institutional_workspaces_no_update
        BEFORE UPDATE ON institutional_workspaces BEGIN SELECT RAISE(ABORT, 'institutional workspaces are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS institutional_workspaces_no_delete
        BEFORE DELETE ON institutional_workspaces BEGIN SELECT RAISE(ABORT, 'institutional workspaces are append-only'); END;

        CREATE TABLE IF NOT EXISTS saved_views (
            view_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id TEXT,
            filters_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_saved_views_owner ON saved_views(owner_id, name);

        CREATE TABLE IF NOT EXISTS activity (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            entity_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_activity_case ON activity(case_id, activity_id);
        CREATE TRIGGER IF NOT EXISTS activity_no_update
        BEFORE UPDATE ON activity BEGIN SELECT RAISE(ABORT, 'activity is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS activity_no_delete
        BEFORE DELETE ON activity BEGIN SELECT RAISE(ABORT, 'activity is append-only'); END;
        """
        with self._lock:
            self._connection.executescript(schema)
            self._connection.execute(
                "INSERT INTO workspace_meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (VERSION,),
            )
            self._connection.commit()

    def health(self) -> Dict[str, Any]:
        with self._lock:
            counts = {}
            for table in ("cases", "revisions", "review_events", "review_templates", "governance_workflows", "review_assignments", "governance_decisions", "monitoring_snapshots", "monitoring_comparisons", "watchlists", "monitoring_alerts", "site_intelligence_events", "stakeholder_actors", "stakeholder_relationships", "stakeholder_incentives", "stakeholder_pressures", "stakeholder_consequences", "catalyst_canvas_handoffs", "comparison_sets", "comparative_evidence_matrices", "scenarios", "scenario_results", "sensitivity_analyses", "decision_studio_handoffs", "publication_briefings", "publication_packages", "public_embeds", "api_keys", "platform_handoffs", "privacy_policies", "retention_assessments", "backup_manifests", "connected_dossiers", "platform_events", "integration_routes", "institutional_workspaces", "saved_views", "activity"):
                counts[table] = int(self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return {"ok": True, "workspace_version": VERSION, "database_path": self.database_path, "counts": counts}

    def _activity(
        self,
        connection: sqlite3.Connection,
        case_id: str,
        event_type: str,
        *,
        entity_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
        created_at: str | None = None,
        activity_id: int | None = None,
    ) -> None:
        values = (case_id, event_type, entity_id, _json_dump(dict(payload or {})), created_at or _iso_now())
        if activity_id is None:
            connection.execute(
                "INSERT INTO activity(case_id, event_type, entity_id, payload_json, created_at) VALUES(?,?,?,?,?)",
                values,
            )
        else:
            connection.execute(
                "INSERT INTO activity(activity_id, case_id, event_type, entity_id, payload_json, created_at) VALUES(?,?,?,?,?,?)",
                (activity_id, *values),
            )

    def _case_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        case_id = row["case_id"]
        revision_count = int(self._connection.execute("SELECT COUNT(*) FROM revisions WHERE case_id=?", (case_id,)).fetchone()[0])
        review_count = int(self._connection.execute("SELECT COUNT(*) FROM review_events WHERE case_id=?", (case_id,)).fetchone()[0])
        workflow = self.get_case_governance_workflow(case_id)
        assignment_count = workflow["assignment_count"] if workflow else 0
        decision_count = workflow["decision_count"] if workflow else 0
        snapshot_count = int(self._connection.execute("SELECT COUNT(*) FROM monitoring_snapshots WHERE case_id=?", (case_id,)).fetchone()[0])
        watch_count = int(self._connection.execute("SELECT COUNT(*) FROM watchlists WHERE case_id=? AND status='active'", (case_id,)).fetchone()[0])
        open_alert_count = int(self._connection.execute("SELECT COUNT(*) FROM monitoring_alerts WHERE case_id=? AND status='open'", (case_id,)).fetchone()[0])
        last_snapshot = self._connection.execute("SELECT captured_at FROM monitoring_snapshots WHERE case_id=? ORDER BY captured_at DESC LIMIT 1", (case_id,)).fetchone()
        critical_alerts = int(self._connection.execute("SELECT COUNT(*) FROM monitoring_alerts WHERE case_id=? AND status='open' AND severity='critical'", (case_id,)).fetchone()[0])
        monitoring_status = "critical" if critical_alerts else "attention_required" if open_alert_count else "current" if snapshot_count else "not_monitored"
        stakeholder_counts = {
            "actors": int(self._connection.execute("SELECT COUNT(*) FROM stakeholder_actors WHERE case_id=?", (case_id,)).fetchone()[0]),
            "relationships": int(self._connection.execute("SELECT COUNT(*) FROM stakeholder_relationships WHERE case_id=?", (case_id,)).fetchone()[0]),
            "incentives": int(self._connection.execute("SELECT COUNT(*) FROM stakeholder_incentives WHERE case_id=?", (case_id,)).fetchone()[0]),
            "pressures": int(self._connection.execute("SELECT COUNT(*) FROM stakeholder_pressures WHERE case_id=?", (case_id,)).fetchone()[0]),
            "consequences": int(self._connection.execute("SELECT COUNT(*) FROM stakeholder_consequences WHERE case_id=?", (case_id,)).fetchone()[0]),
        }
        stakeholder_summary = self.get_stakeholder_intelligence(case_id, generated_at=row["updated_at"]) if stakeholder_counts["actors"] else None
        comparative_counts = {
            "comparison_sets": int(self._connection.execute("SELECT COUNT(*) FROM comparison_sets WHERE case_id=?", (case_id,)).fetchone()[0]),
            "scenarios": int(self._connection.execute("SELECT COUNT(*) FROM scenarios WHERE case_id=?", (case_id,)).fetchone()[0]),
            "scenario_results": int(self._connection.execute("SELECT COUNT(*) FROM scenario_results WHERE case_id=?", (case_id,)).fetchone()[0]),
            "sensitivity_analyses": int(self._connection.execute("SELECT COUNT(*) FROM sensitivity_analyses WHERE case_id=?", (case_id,)).fetchone()[0]),
            "decision_studio_handoffs": int(self._connection.execute("SELECT COUNT(*) FROM decision_studio_handoffs WHERE case_id=?", (case_id,)).fetchone()[0]),
        }
        comparative_status = "not_started" if comparative_counts["comparison_sets"] == 0 else "scenario_ready" if comparative_counts["scenario_results"] else "comparison_ready"
        publication_counts = {
            "briefings": int(self._connection.execute("SELECT COUNT(*) FROM publication_briefings WHERE case_id=?", (case_id,)).fetchone()[0]),
            "packages": int(self._connection.execute("SELECT COUNT(*) FROM publication_packages WHERE case_id=?", (case_id,)).fetchone()[0]),
            "embeds": int(self._connection.execute("SELECT COUNT(*) FROM public_embeds WHERE case_id=?", (case_id,)).fetchone()[0]),
            "handoffs": int(self._connection.execute("SELECT COUNT(*) FROM platform_handoffs WHERE case_id=?", (case_id,)).fetchone()[0]),
        }
        published_count = int(self._connection.execute("SELECT COUNT(*) FROM publication_packages WHERE case_id=? AND status='published'", (case_id,)).fetchone()[0])
        publication_status = "published" if published_count else "package_ready" if publication_counts["packages"] else "briefing_ready" if publication_counts["briefings"] else "not_started"
        case = {
            "case_id": case_id,
            "organization_id": row["organization_id"],
            "project_id": row["project_id"],
            "title": row["title"],
            "summary": row["summary"],
            "status": row["status"],
            "priority": row["priority"],
            "tags": _json_load(row["tags_json"]),
            "archived": row["archived_at"] is not None,
            "archived_at": row["archived_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "current_revision": int(row["current_revision"]),
            "latest_record_id": row["latest_record_id"],
            "revision_count": revision_count,
            "review_event_count": review_count,
            "assignment_count": assignment_count,
            "governance_decision_count": decision_count,
            "workflow_status": workflow["status"] if workflow else None,
            "current_stage": workflow["current_stage"] if workflow else None,
            "final_disposition": workflow["final_disposition"] if workflow else None,
            "approval_valid_until": workflow["approval_valid_until"] if workflow else None,
            "reassessment_at": workflow["reassessment_at"] if workflow else None,
            "publication_allowed": workflow["publication_allowed"] if workflow else False,
            "monitoring_snapshot_count": snapshot_count,
            "watch_count": watch_count,
            "open_alert_count": open_alert_count,
            "last_monitored_at": last_snapshot["captured_at"] if last_snapshot else None,
            "monitoring_status": monitoring_status,
            "stakeholder_actor_count": stakeholder_counts["actors"],
            "stakeholder_relationship_count": stakeholder_counts["relationships"],
            "stakeholder_incentive_count": stakeholder_counts["incentives"],
            "stakeholder_pressure_count": stakeholder_counts["pressures"],
            "stakeholder_consequence_count": stakeholder_counts["consequences"],
            "suggested_stakeholder_pressure": stakeholder_summary["suggested_stakeholder_pressure"] if stakeholder_summary else None,
            "comparison_set_count": comparative_counts["comparison_sets"],
            "scenario_count": comparative_counts["scenarios"],
            "evaluated_scenario_count": comparative_counts["scenario_results"],
            "sensitivity_analysis_count": comparative_counts["sensitivity_analyses"],
            "decision_studio_handoff_count": comparative_counts["decision_studio_handoffs"],
            "comparative_status": comparative_status,
            "publication_briefing_count": publication_counts["briefings"],
            "publication_package_count": publication_counts["packages"],
            "public_embed_count": publication_counts["embeds"],
            "platform_handoff_count": publication_counts["handoffs"],
            "publication_status": publication_status,
        }
        _schema_error("case", case, CASE_SCHEMA_PATH)
        return case

    def create_case(
        self,
        *,
        title: str,
        summary: str = "",
        organization_id: str | None = None,
        project_id: str | None = None,
        status: str = "draft",
        priority: str = "normal",
        tags: Sequence[str] | None = None,
        case_id: str | None = None,
        created_at: str | None = None,
        initial_payload: Mapping[str, Any] | None = None,
        created_by: str | None = None,
        change_note: str = "Initial case revision.",
    ) -> Dict[str, Any]:
        normalized_id = _urn_uuid(case_id, "case_id")
        timestamp = _validate_datetime(created_at, "created_at") if created_at else _iso_now()
        normalized_title = _text(title, "title", required=True, maximum=500)
        normalized_summary = _text(summary, "summary", maximum=20000)
        normalized_status = _choice(status, "status", CASE_STATUSES, "draft")
        normalized_priority = _choice(priority, "priority", CASE_PRIORITIES, "normal")
        normalized_tags = _tags(tags)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO cases(case_id, organization_id, project_id, title, summary, status, priority, tags_json, archived_at, created_at, updated_at, current_revision, latest_record_id) "
                    "VALUES(?,?,?,?,?,?,?,?,NULL,?,?,0,NULL)",
                    (
                        normalized_id, _nullable_text(organization_id, "organization_id"),
                        _nullable_text(project_id, "project_id"), normalized_title, normalized_summary,
                        normalized_status, normalized_priority, _json_dump(normalized_tags), timestamp, timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"case already exists: {normalized_id}") from exc
            self._activity(connection, normalized_id, "case_created", entity_id=normalized_id, payload={"title": normalized_title}, created_at=timestamp)
        if initial_payload is not None:
            record = build_narrative_risk_record(initial_payload, case_id=normalized_id, generated_at=timestamp)
            self.add_revision(normalized_id, record=record, created_by=created_by, change_note=change_note, created_at=timestamp)
        return self.get_case(normalized_id)

    def get_case(self, case_id: str, *, include_details: bool = False) -> Dict[str, Any]:
        normalized_id = _urn_uuid(case_id, "case_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM cases WHERE case_id=?", (normalized_id,)).fetchone()
            if row is None:
                raise NarrativeRiskValidationError(f"case not found: {normalized_id}")
            case = self._case_from_row(row)
            if include_details:
                case["revisions"] = self.list_revisions(normalized_id)
                case["review_events"] = self.list_review_events(normalized_id)
                case["governance_workflow"] = self.get_case_governance_workflow(normalized_id, include_details=True)
                case["monitoring_snapshots"] = self.list_monitoring_snapshots(normalized_id)
                case["monitoring_comparisons"] = self.list_monitoring_comparisons(normalized_id)
                case["watchlists"] = self.list_watchlists(case_id=normalized_id)
                case["monitoring_alerts"] = self.list_monitoring_alerts(case_id=normalized_id)
                case["site_intelligence_events"] = self.list_site_intelligence_events(normalized_id)
                case["activity"] = self.list_activity(normalized_id)
            return case

    def list_cases(
        self,
        *,
        query: str = "",
        organization_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        tags: Sequence[str] | None = None,
        archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise NarrativeRiskValidationError("limit must be an integer between 1 and 1000")
        if not isinstance(offset, int) or offset < 0:
            raise NarrativeRiskValidationError("offset must be a non-negative integer")
        clauses = ["archived_at IS NOT NULL" if archived else "archived_at IS NULL"]
        parameters: List[Any] = []
        if query:
            cleaned = _text(query, "query", maximum=500)
            clauses.append("(LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)")
            needle = f"%{cleaned.casefold()}%"
            parameters.extend([needle, needle])
        if organization_id is not None:
            clauses.append("organization_id = ?")
            parameters.append(_nullable_text(organization_id, "organization_id"))
        if project_id is not None:
            clauses.append("project_id = ?")
            parameters.append(_nullable_text(project_id, "project_id"))
        if status is not None:
            clauses.append("status = ?")
            parameters.append(_choice(status, "status", CASE_STATUSES, "draft"))
        if priority is not None:
            clauses.append("priority = ?")
            parameters.append(_choice(priority, "priority", CASE_PRIORITIES, "normal"))
        wanted_tags = {tag.casefold() for tag in _tags(tags)}
        sql = "SELECT * FROM cases WHERE " + " AND ".join(clauses) + " ORDER BY updated_at DESC, case_id LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
        with self._lock:
            rows = self._connection.execute(sql, parameters).fetchall()
            cases = [self._case_from_row(row) for row in rows]
        if wanted_tags:
            cases = [case for case in cases if wanted_tags.issubset({tag.casefold() for tag in case["tags"]})]
        return cases

    def update_case(self, case_id: str, changes: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(changes, Mapping):
            raise NarrativeRiskValidationError("case changes must be a JSON object")
        allowed = {"title", "summary", "organization_id", "project_id", "status", "priority", "tags"}
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise NarrativeRiskValidationError(f"unsupported case field(s): {', '.join(unknown)}")
        normalized_id = _urn_uuid(case_id, "case_id")
        if not changes:
            return self.get_case(normalized_id)
        setters: List[str] = []
        values: List[Any] = []
        normalized_changes: Dict[str, Any] = {}
        for field, value in changes.items():
            if field == "title": normalized = _text(value, field, required=True, maximum=500)
            elif field == "summary": normalized = _text(value, field, maximum=20000)
            elif field in {"organization_id", "project_id"}: normalized = _nullable_text(value, field)
            elif field == "status": normalized = _choice(value, field, CASE_STATUSES, "draft")
            elif field == "priority": normalized = _choice(value, field, CASE_PRIORITIES, "normal")
            elif field == "tags": normalized = _tags(value)
            else:  # pragma: no cover
                continue
            setters.append(f"{field if field != 'tags' else 'tags_json'} = ?")
            values.append(_json_dump(normalized) if field == "tags" else normalized)
            normalized_changes[field] = normalized
        timestamp = _iso_now()
        setters.append("updated_at = ?")
        values.extend([timestamp, normalized_id])
        with self._transaction() as connection:
            old = connection.execute("SELECT status FROM cases WHERE case_id=?", (normalized_id,)).fetchone()
            if old is None:
                raise NarrativeRiskValidationError(f"case not found: {normalized_id}")
            connection.execute(f"UPDATE cases SET {', '.join(setters)} WHERE case_id=?", values)
            self._activity(connection, normalized_id, "case_updated", entity_id=normalized_id, payload=normalized_changes, created_at=timestamp)
            if "status" in normalized_changes and normalized_changes["status"] != old["status"]:
                self._activity(connection, normalized_id, "case_status_changed", entity_id=normalized_id, payload={"from": old["status"], "to": normalized_changes["status"]}, created_at=timestamp)
        return self.get_case(normalized_id)

    def archive_case(self, case_id: str, *, archived_at: str | None = None) -> Dict[str, Any]:
        normalized_id = _urn_uuid(case_id, "case_id")
        timestamp = _validate_datetime(archived_at, "archived_at") if archived_at else _iso_now()
        with self._transaction() as connection:
            result = connection.execute("UPDATE cases SET archived_at=?, updated_at=? WHERE case_id=?", (timestamp, timestamp, normalized_id))
            if result.rowcount == 0:
                raise NarrativeRiskValidationError(f"case not found: {normalized_id}")
            self._activity(connection, normalized_id, "case_archived", entity_id=normalized_id, created_at=timestamp)
        return self.get_case(normalized_id)

    def restore_case(self, case_id: str) -> Dict[str, Any]:
        normalized_id = _urn_uuid(case_id, "case_id")
        timestamp = _iso_now()
        with self._transaction() as connection:
            result = connection.execute("UPDATE cases SET archived_at=NULL, updated_at=? WHERE case_id=?", (timestamp, normalized_id))
            if result.rowcount == 0:
                raise NarrativeRiskValidationError(f"case not found: {normalized_id}")
            self._activity(connection, normalized_id, "case_restored", entity_id=normalized_id, created_at=timestamp)
        return self.get_case(normalized_id)

    def add_revision(
        self,
        case_id: str,
        *,
        record: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
        human_decision: Mapping[str, Any] | None = None,
        created_by: str | None = None,
        change_note: str = "",
        revision_id: str | None = None,
        created_at: str | None = None,
    ) -> Dict[str, Any]:
        normalized_case_id = _urn_uuid(case_id, "case_id")
        if (record is None) == (payload is None):
            raise NarrativeRiskValidationError("provide exactly one of record or payload")
        timestamp = _validate_datetime(created_at, "created_at") if created_at else _iso_now()
        if record is None:
            record_data = build_narrative_risk_record(payload or {}, case_id=normalized_case_id, generated_at=timestamp, human_decision=human_decision)
        else:
            record_data = deepcopy(dict(record))
            validate_narrative_risk_record(record_data)
        if record_data["identifiers"]["case_id"] != normalized_case_id:
            raise NarrativeRiskValidationError("record case_id does not match the workspace case")
        normalized_revision_id = _urn_uuid(revision_id, "revision_id")
        record_hash = sha256_digest(record_data)
        created_by_value = _nullable_text(created_by, "created_by")
        note = _text(change_note, "change_note", maximum=20000)
        with self._transaction() as connection:
            case = connection.execute("SELECT current_revision FROM cases WHERE case_id=?", (normalized_case_id,)).fetchone()
            if case is None:
                raise NarrativeRiskValidationError(f"case not found: {normalized_case_id}")
            revision_number = int(case["current_revision"]) + 1
            try:
                connection.execute(
                    "INSERT INTO revisions(revision_id, case_id, revision_number, record_id, record_json, record_sha256, created_at, created_by, change_note) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        normalized_revision_id, normalized_case_id, revision_number,
                        record_data["identifiers"]["record_id"], _json_dump(record_data), record_hash,
                        timestamp, created_by_value, note,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError("revision or record identifier already exists") from exc
            connection.execute(
                "UPDATE cases SET current_revision=?, latest_record_id=?, updated_at=? WHERE case_id=?",
                (revision_number, record_data["identifiers"]["record_id"], timestamp, normalized_case_id),
            )
            self._activity(
                connection, normalized_case_id, "revision_added", entity_id=normalized_revision_id,
                payload={"revision_number": revision_number, "record_id": record_data["identifiers"]["record_id"], "record_sha256": record_hash},
                created_at=timestamp,
            )
        return self.get_revision(normalized_revision_id)

    def _revision_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        revision = {
            "revision_id": row["revision_id"], "case_id": row["case_id"],
            "revision_number": int(row["revision_number"]), "record_id": row["record_id"],
            "record_sha256": row["record_sha256"], "created_at": row["created_at"],
            "created_by": row["created_by"], "change_note": row["change_note"],
            "record": _json_load(row["record_json"]),
        }
        _schema_error("revision", revision, REVISION_SCHEMA_PATH)
        if sha256_digest(revision["record"]) != revision["record_sha256"]:
            raise NarrativeRiskValidationError(f"revision record hash mismatch: {revision['revision_id']}")
        return revision

    def get_revision(self, revision_id: str) -> Dict[str, Any]:
        normalized_id = _urn_uuid(revision_id, "revision_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM revisions WHERE revision_id=?", (normalized_id,)).fetchone()
            if row is None:
                raise NarrativeRiskValidationError(f"revision not found: {normalized_id}")
            return self._revision_from_row(row)

    def list_revisions(self, case_id: str) -> List[Dict[str, Any]]:
        normalized_id = _urn_uuid(case_id, "case_id")
        with self._lock:
            rows = self._connection.execute("SELECT * FROM revisions WHERE case_id=? ORDER BY revision_number", (normalized_id,)).fetchall()
            return [self._revision_from_row(row) for row in rows]

    def add_review_event(
        self,
        case_id: str,
        *,
        event_type: str = "comment",
        revision_id: str | None = None,
        author_id: str | None = None,
        author_name: str | None = None,
        body: str = "",
        metadata: Mapping[str, Any] | None = None,
        event_id: str | None = None,
        created_at: str | None = None,
    ) -> Dict[str, Any]:
        normalized_case_id = _urn_uuid(case_id, "case_id")
        normalized_event_id = _urn_uuid(event_id, "event_id")
        normalized_revision_id = _urn_uuid(revision_id, "revision_id") if revision_id is not None else None
        normalized_type = _choice(event_type, "event_type", REVIEW_EVENT_TYPES, "comment")
        normalized_body = _text(body, "body", maximum=50000)
        if normalized_type == "comment" and not normalized_body:
            raise NarrativeRiskValidationError("body is required for comment review events")
        if metadata is None:
            metadata_value: Dict[str, Any] = {}
        elif isinstance(metadata, Mapping):
            metadata_value = deepcopy(dict(metadata))
        else:
            raise NarrativeRiskValidationError("metadata must be a JSON object")
        timestamp = _validate_datetime(created_at, "created_at") if created_at else _iso_now()
        event = {
            "event_id": normalized_event_id, "case_id": normalized_case_id,
            "revision_id": normalized_revision_id, "event_type": normalized_type,
            "author_id": _nullable_text(author_id, "author_id"),
            "author_name": _nullable_text(author_name, "author_name"),
            "body": normalized_body, "created_at": timestamp, "metadata": metadata_value,
        }
        _schema_error("review event", event, REVIEW_EVENT_SCHEMA_PATH)
        with self._transaction() as connection:
            if connection.execute("SELECT 1 FROM cases WHERE case_id=?", (normalized_case_id,)).fetchone() is None:
                raise NarrativeRiskValidationError(f"case not found: {normalized_case_id}")
            if normalized_revision_id is not None:
                revision = connection.execute("SELECT case_id FROM revisions WHERE revision_id=?", (normalized_revision_id,)).fetchone()
                if revision is None or revision["case_id"] != normalized_case_id:
                    raise NarrativeRiskValidationError("revision_id does not reference a revision in this case")
            try:
                connection.execute(
                    "INSERT INTO review_events(event_id, case_id, revision_id, event_type, author_id, author_name, body, created_at, metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        normalized_event_id, normalized_case_id, normalized_revision_id, normalized_type,
                        event["author_id"], event["author_name"], normalized_body, timestamp, _json_dump(metadata_value),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"review event already exists: {normalized_event_id}") from exc
            connection.execute("UPDATE cases SET updated_at=? WHERE case_id=?", (timestamp, normalized_case_id))
            self._activity(connection, normalized_case_id, "review_event_added", entity_id=normalized_event_id, payload={"event_type": normalized_type, "revision_id": normalized_revision_id}, created_at=timestamp)
        return event

    def list_review_events(self, case_id: str) -> List[Dict[str, Any]]:
        normalized_id = _urn_uuid(case_id, "case_id")
        with self._lock:
            rows = self._connection.execute("SELECT * FROM review_events WHERE case_id=? ORDER BY created_at, event_id", (normalized_id,)).fetchall()
        events = []
        for row in rows:
            event = {
                "event_id": row["event_id"], "case_id": row["case_id"], "revision_id": row["revision_id"],
                "event_type": row["event_type"], "author_id": row["author_id"], "author_name": row["author_name"],
                "body": row["body"], "created_at": row["created_at"], "metadata": _json_load(row["metadata_json"]),
            }
            _schema_error("review event", event, REVIEW_EVENT_SCHEMA_PATH)
            events.append(event)
        return events

    def list_activity(self, case_id: str) -> List[Dict[str, Any]]:
        normalized_id = _urn_uuid(case_id, "case_id")
        with self._lock:
            rows = self._connection.execute("SELECT * FROM activity WHERE case_id=? ORDER BY activity_id", (normalized_id,)).fetchall()
        return [
            {
                "activity_id": int(row["activity_id"]), "case_id": row["case_id"],
                "event_type": row["event_type"], "entity_id": row["entity_id"],
                "payload": _json_load(row["payload_json"]), "created_at": row["created_at"],
            }
            for row in rows
        ]

    def save_view(
        self,
        *,
        name: str,
        filters: Mapping[str, Any] | None = None,
        owner_id: str | None = None,
        view_id: str | None = None,
        created_at: str | None = None,
    ) -> Dict[str, Any]:
        normalized_id = _urn_uuid(view_id, "view_id")
        normalized_name = _text(name, "name", required=True, maximum=500)
        source = {} if filters is None else filters
        if not isinstance(source, Mapping):
            raise NarrativeRiskValidationError("filters must be a JSON object")
        unknown = sorted(set(source) - SAVED_VIEW_FIELDS)
        if unknown:
            raise NarrativeRiskValidationError(f"unsupported saved-view filter(s): {', '.join(unknown)}")
        normalized_filters: Dict[str, Any] = {}
        if "query" in source: normalized_filters["query"] = _text(source["query"], "filters.query", maximum=500)
        if "organization_id" in source: normalized_filters["organization_id"] = _nullable_text(source["organization_id"], "filters.organization_id")
        if "project_id" in source: normalized_filters["project_id"] = _nullable_text(source["project_id"], "filters.project_id")
        if "status" in source: normalized_filters["status"] = None if source["status"] is None else _choice(source["status"], "filters.status", CASE_STATUSES, "draft")
        if "priority" in source: normalized_filters["priority"] = None if source["priority"] is None else _choice(source["priority"], "filters.priority", CASE_PRIORITIES, "normal")
        if "tags" in source: normalized_filters["tags"] = _tags(source["tags"])
        if "archived" in source:
            if not isinstance(source["archived"], bool): raise NarrativeRiskValidationError("filters.archived must be a boolean")
            normalized_filters["archived"] = source["archived"]
        timestamp = _validate_datetime(created_at, "created_at") if created_at else _iso_now()
        view = {
            "view_id": normalized_id, "name": normalized_name,
            "owner_id": _nullable_text(owner_id, "owner_id"), "filters": normalized_filters,
            "created_at": timestamp, "updated_at": timestamp,
        }
        _schema_error("saved view", view, SAVED_VIEW_SCHEMA_PATH)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO saved_views(view_id, name, owner_id, filters_json, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                    (normalized_id, normalized_name, view["owner_id"], _json_dump(normalized_filters), timestamp, timestamp),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"saved view already exists: {normalized_id}") from exc
        return view

    def list_saved_views(self, *, owner_id: str | None = None) -> List[Dict[str, Any]]:
        with self._lock:
            if owner_id is None:
                rows = self._connection.execute("SELECT * FROM saved_views ORDER BY name, view_id").fetchall()
            else:
                rows = self._connection.execute("SELECT * FROM saved_views WHERE owner_id=? ORDER BY name, view_id", (_nullable_text(owner_id, "owner_id"),)).fetchall()
        views = []
        for row in rows:
            view = {
                "view_id": row["view_id"], "name": row["name"], "owner_id": row["owner_id"],
                "filters": _json_load(row["filters_json"]), "created_at": row["created_at"], "updated_at": row["updated_at"],
            }
            _schema_error("saved view", view, SAVED_VIEW_SCHEMA_PATH)
            views.append(view)
        return views

    def export_case_bundle(self, case_id: str, *, exported_at: str | None = None) -> Dict[str, Any]:
        timestamp = _validate_datetime(exported_at, "exported_at") if exported_at else _iso_now()
        case = self.get_case(case_id)
        bundle = {
            "bundle_type": BUNDLE_TYPE, "bundle_version": VERSION, "exported_at": timestamp,
            "case": case, "revisions": self.list_revisions(case["case_id"]),
            "review_events": self.list_review_events(case["case_id"]),
            "governance_workflow": self.get_case_governance_workflow(case["case_id"]),
            "review_assignments": self.list_review_assignments(case_id=case["case_id"]),
            "governance_decisions": self.list_governance_decisions(case_id=case["case_id"]),
            "monitoring_snapshots": self.list_monitoring_snapshots(case["case_id"]),
            "monitoring_comparisons": self.list_monitoring_comparisons(case["case_id"]),
            "watchlists": self.list_watchlists(case_id=case["case_id"]),
            "monitoring_alerts": self.list_monitoring_alerts(case_id=case["case_id"]),
            "site_intelligence_events": self.list_site_intelligence_events(case["case_id"]),
            "stakeholder_actors": self.list_stakeholder_actors(case["case_id"]),
            "stakeholder_relationships": self.list_stakeholder_relationships(case["case_id"]),
            "stakeholder_incentives": self.list_stakeholder_incentives(case["case_id"]),
            "stakeholder_pressures": self.list_stakeholder_pressures(case["case_id"]),
            "stakeholder_consequences": self.list_stakeholder_consequences(case["case_id"]),
            "stakeholder_intelligence": self.get_stakeholder_intelligence(case["case_id"]),
            "catalyst_canvas_handoffs": self.list_canvas_handoffs(case["case_id"]),
            "comparison_sets": self.list_comparison_sets(case_id=case["case_id"]),
            "comparative_evidence_matrices": [matrix for comparison in self.list_comparison_sets(case_id=case["case_id"]) for matrix in self.list_comparative_evidence_matrices(comparison["comparison_id"])],
            "scenarios": self.list_scenarios(case_id=case["case_id"]),
            "scenario_results": self.list_scenario_results(case_id=case["case_id"]),
            "sensitivity_analyses": [analysis for comparison in self.list_comparison_sets(case_id=case["case_id"]) for analysis in self.list_sensitivity_analyses(comparison["comparison_id"])],
            "comparative_portfolio": self.get_comparative_portfolio(case["case_id"], generated_at=timestamp),
            "decision_studio_handoffs": self.list_decision_studio_handoffs(case["case_id"]),
            "publication_briefings": self.list_publication_briefings(case["case_id"]),
            "publication_packages": self.list_publication_packages(case["case_id"]),
            "public_embeds": self.list_public_embeds(case["case_id"]),
            "platform_handoffs": self.list_platform_handoffs(case["case_id"]),
            "retention_assessments": self.list_retention_assessments(case["case_id"]),
            "connected_dossiers": self.list_connected_dossiers(case["case_id"]),
            "platform_events": self.list_platform_events(case_id=case["case_id"]),
            "integration_routes": self.list_integration_routes(case_id=case["case_id"]),
            "activity": self.list_activity(case["case_id"]),
        }
        bundle["bundle_sha256"] = sha256_digest(bundle)
        _schema_error("workspace bundle", bundle, WORKSPACE_BUNDLE_SCHEMA_PATH)
        return bundle

    @staticmethod
    def verify_bundle(bundle: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(bundle, Mapping):
            raise NarrativeRiskValidationError("bundle must be a JSON object")
        candidate = deepcopy(dict(bundle))
        _schema_error("workspace bundle", candidate, WORKSPACE_BUNDLE_SCHEMA_PATH)
        expected = candidate.pop("bundle_sha256")
        actual = sha256_digest(candidate)
        revision_checks = []
        for revision in bundle["revisions"]:
            record_ok = sha256_digest(revision["record"]) == revision["record_sha256"]
            case_ok = revision["case_id"] == bundle["case"]["case_id"]
            revision_checks.append({"revision_id": revision["revision_id"], "record_hash_match": record_ok, "case_id_match": case_ok})
        return {
            "bundle_sha256_match": expected == actual,
            "expected_bundle_sha256": expected,
            "actual_bundle_sha256": actual,
            "revision_checks": revision_checks,
            "all_revision_hashes_match": all(item["record_hash_match"] for item in revision_checks),
            "all_case_ids_match": all(item["case_id_match"] for item in revision_checks),
            "governance_case_ids_match": all(
                item.get("case_id") == bundle["case"]["case_id"]
                for item in ([bundle["governance_workflow"]] if bundle.get("governance_workflow") else [])
                + list(bundle.get("review_assignments", [])) + list(bundle.get("governance_decisions", []))
            ),
            "monitoring_case_ids_match": all(
                item.get("case_id") == bundle["case"]["case_id"]
                for item in list(bundle.get("monitoring_snapshots", [])) + list(bundle.get("monitoring_comparisons", []))
                + list(bundle.get("watchlists", [])) + list(bundle.get("monitoring_alerts", []))
                + list(bundle.get("site_intelligence_events", []))
            ),
            "all_snapshot_hashes_match": all(
                sha256_digest({k: v for k, v in item.items() if k != "snapshot_sha256"}) == item["snapshot_sha256"]
                for item in bundle.get("monitoring_snapshots", [])
            ),
            "all_comparison_hashes_match": all(
                sha256_digest({k: v for k, v in item.items() if k != "comparison_sha256"}) == item["comparison_sha256"]
                for item in bundle.get("monitoring_comparisons", [])
            ),
            "stakeholder_case_ids_match": all(
                item.get("case_id") == bundle["case"]["case_id"]
                for item in list(bundle.get("stakeholder_actors", [])) + list(bundle.get("stakeholder_relationships", []))
                + list(bundle.get("stakeholder_incentives", [])) + list(bundle.get("stakeholder_pressures", []))
                + list(bundle.get("stakeholder_consequences", []))
            ) and bundle.get("stakeholder_intelligence", {}).get("case_id") == bundle["case"]["case_id"],
            "stakeholder_intelligence_hash_match": sha256_digest({k: v for k, v in bundle["stakeholder_intelligence"].items() if k != "intelligence_sha256"}) == bundle["stakeholder_intelligence"]["intelligence_sha256"],
            "comparative_case_ids_match": all(
                item.get("case_id") == bundle["case"]["case_id"]
                for item in list(bundle.get("comparison_sets", [])) + list(bundle.get("comparative_evidence_matrices", []))
                + list(bundle.get("scenarios", [])) + list(bundle.get("scenario_results", []))
                + list(bundle.get("sensitivity_analyses", [])) + list(bundle.get("decision_studio_handoffs", []))
            ) and bundle.get("comparative_portfolio", {}).get("case_id") == bundle["case"]["case_id"],
            "comparative_hashes_match": all(
                sha256_digest({k: v for k, v in item.items() if k != hash_field}) == item[hash_field]
                for values, hash_field in (
                    (bundle.get("comparative_evidence_matrices", []), "matrix_sha256"),
                    (bundle.get("scenario_results", []), "result_sha256"),
                    (bundle.get("sensitivity_analyses", []), "analysis_sha256"),
                    (bundle.get("decision_studio_handoffs", []), "handoff_sha256"),
                ) for item in values
            ) and sha256_digest({k: v for k, v in bundle["comparative_portfolio"].items() if k != "portfolio_sha256"}) == bundle["comparative_portfolio"]["portfolio_sha256"],
            "publication_case_ids_match": all(
                item.get("case_id") == bundle["case"]["case_id"]
                for item in list(bundle.get("publication_briefings", [])) + list(bundle.get("publication_packages", []))
                + list(bundle.get("public_embeds", [])) + list(bundle.get("platform_handoffs", []))
            ),
            "privacy_case_ids_match": all(item.get("case_id") == bundle["case"]["case_id"] for item in bundle.get("retention_assessments", [])),
            "privacy_hashes_match": all(sha256_digest({k: v for k, v in item.items() if k != "assessment_sha256"}) == item["assessment_sha256"] for item in bundle.get("retention_assessments", [])),
            "publication_hashes_match": all(
                sha256_digest({k: v for k, v in item.items() if k != hash_field}) == item[hash_field]
                for values, hash_field in (
                    (bundle.get("publication_briefings", []), "briefing_sha256"),
                    (bundle.get("publication_packages", []), "package_sha256"),
                    (bundle.get("public_embeds", []), "embed_sha256"),
                    (bundle.get("platform_handoffs", []), "handoff_sha256"),
                ) for item in values
            ),
            "connected_case_ids_match": all(
                item.get("case_id") == bundle["case"]["case_id"]
                for item in list(bundle.get("connected_dossiers", [])) + list(bundle.get("platform_events", []))
                + list(bundle.get("integration_routes", []))
            ),
            "connected_hashes_match": all(
                sha256_digest({k: v for k, v in item.items() if k != hash_field}) == item[hash_field]
                for values, hash_field in (
                    (bundle.get("connected_dossiers", []), "dossier_sha256"),
                    (bundle.get("platform_events", []), "event_sha256"),
                    (bundle.get("integration_routes", []), "route_sha256"),
                ) for item in values
            ),
        }

    def import_case_bundle(self, bundle: Mapping[str, Any]) -> Dict[str, Any]:
        report = self.verify_bundle(bundle)
        if not report["bundle_sha256_match"]:
            raise NarrativeRiskValidationError("workspace bundle_sha256 does not match the bundle payload")
        if not report["all_revision_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a revision record hash mismatch")
        if not report["all_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a revision for another case")
        if not report["governance_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains governance records for another case")
        if not report["monitoring_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains monitoring records for another case")
        if not report["all_snapshot_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a monitoring snapshot hash mismatch")
        if not report["all_comparison_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a monitoring comparison hash mismatch")
        if not report["stakeholder_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains stakeholder records for another case")
        if not report["stakeholder_intelligence_hash_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a stakeholder intelligence hash mismatch")
        if not report["comparative_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains comparative records for another case")
        if not report["comparative_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a comparative artifact hash mismatch")
        if not report["publication_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains publication records for another case")
        if not report["publication_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a publication artifact hash mismatch")
        if not report["privacy_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains retention assessments for another case")
        if not report["privacy_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a retention assessment hash mismatch")
        case = bundle["case"]
        case_id = case["case_id"]
        with self._transaction() as connection:
            if connection.execute("SELECT 1 FROM cases WHERE case_id=?", (case_id,)).fetchone() is not None:
                raise NarrativeRiskValidationError(f"case already exists: {case_id}")
            connection.execute(
                "INSERT INTO cases(case_id, organization_id, project_id, title, summary, status, priority, tags_json, archived_at, created_at, updated_at, current_revision, latest_record_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    case_id, case["organization_id"], case["project_id"], case["title"], case["summary"], case["status"],
                    case["priority"], _json_dump(case["tags"]), case["archived_at"], case["created_at"], case["updated_at"],
                    case["current_revision"], case["latest_record_id"],
                ),
            )
            for revision in bundle["revisions"]:
                validate_narrative_risk_record(revision["record"])
                connection.execute(
                    "INSERT INTO revisions(revision_id, case_id, revision_number, record_id, record_json, record_sha256, created_at, created_by, change_note) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        revision["revision_id"], revision["case_id"], revision["revision_number"], revision["record_id"],
                        _json_dump(revision["record"]), revision["record_sha256"], revision["created_at"], revision["created_by"], revision["change_note"],
                    ),
                )
            for event in bundle["review_events"]:
                connection.execute(
                    "INSERT INTO review_events(event_id, case_id, revision_id, event_type, author_id, author_name, body, created_at, metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        event["event_id"], event["case_id"], event["revision_id"], event["event_type"], event["author_id"],
                        event["author_name"], event["body"], event["created_at"], _json_dump(event["metadata"]),
                    ),
                )
            workflow = bundle.get("governance_workflow")
            if workflow is not None:
                connection.execute(
                    "INSERT INTO governance_workflows(workflow_id,case_id,revision_id,template_id,template_snapshot_json,status,current_stage,started_at,due_at,completed_at,created_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (workflow["workflow_id"], workflow["case_id"], workflow["revision_id"], workflow["template_id"],
                     _json_dump(workflow["template_snapshot"]), workflow["status"] if workflow["status"] != "expired" else "approved",
                     workflow["current_stage"], workflow["started_at"], workflow["due_at"], workflow["completed_at"],
                     workflow["created_by"], workflow["updated_at"]),
                )
            for assignment in bundle.get("review_assignments", []):
                connection.execute(
                    "INSERT INTO review_assignments(assignment_id,case_id,revision_id,workflow_id,stage,reviewer_id,reviewer_name,reviewer_role,status,required,instructions,created_at,created_by,due_at,accepted_at,completed_at,escalated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (assignment["assignment_id"], assignment["case_id"], assignment["revision_id"], assignment["workflow_id"],
                     assignment["stage"], assignment["reviewer_id"], assignment["reviewer_name"], assignment["reviewer_role"],
                     assignment["status"], int(assignment["required"]), assignment["instructions"], assignment["created_at"],
                     assignment["created_by"], assignment["due_at"], assignment["accepted_at"], assignment["completed_at"], assignment["escalated_at"]),
                )
            for decision in bundle.get("governance_decisions", []):
                connection.execute(
                    "INSERT INTO governance_decisions(decision_id,case_id,revision_id,workflow_id,assignment_id,stage,disposition,decided_by,decided_by_name,decider_role,decided_at,rationale,conditions_json,required_wording_json,publication_restrictions_json,disclosures_json,valid_until,reassessment_at,supersedes_decision_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (decision["decision_id"], decision["case_id"], decision["revision_id"], decision["workflow_id"], decision["assignment_id"],
                     decision["stage"], decision["disposition"], decision["decided_by"], decision["decided_by_name"],
                     decision["decider_role"], decision["decided_at"], decision["rationale"], _json_dump(decision["conditions"]),
                     _json_dump(decision["required_wording"]), _json_dump(decision["publication_restrictions"]),
                     _json_dump(decision["disclosures"]), decision["valid_until"], decision["reassessment_at"], decision["supersedes_decision_id"]),
                )
            for snapshot in bundle.get("monitoring_snapshots", []):
                connection.execute(
                    "INSERT INTO monitoring_snapshots(snapshot_id,case_id,revision_id,record_id,captured_at,trigger,snapshot_json,snapshot_sha256) VALUES(?,?,?,?,?,?,?,?)",
                    (snapshot["snapshot_id"], snapshot["case_id"], snapshot["revision_id"], snapshot["record_id"], snapshot["captured_at"], snapshot["trigger"], _json_dump(snapshot), snapshot["snapshot_sha256"]),
                )
            for comparison in bundle.get("monitoring_comparisons", []):
                connection.execute(
                    "INSERT INTO monitoring_comparisons(comparison_id,case_id,from_snapshot_id,to_snapshot_id,compared_at,materiality_score,severity,comparison_json,comparison_sha256) VALUES(?,?,?,?,?,?,?,?,?)",
                    (comparison["comparison_id"], comparison["case_id"], comparison["from_snapshot_id"], comparison["to_snapshot_id"], comparison["compared_at"], comparison["materiality_score"], comparison["severity"], _json_dump(comparison), comparison["comparison_sha256"]),
                )
            for watch in bundle.get("watchlists", []):
                connection.execute(
                    "INSERT INTO watchlists(watch_id,case_id,name,status,cadence,trigger_types_json,source_ids_json,created_at,updated_at,last_checked_at,next_check_at,created_by,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (watch["watch_id"], watch["case_id"], watch["name"], watch["status"], watch["cadence"], _json_dump(watch["trigger_types"]), _json_dump(watch["source_ids"]), watch["created_at"], watch["updated_at"], watch["last_checked_at"], watch["next_check_at"], watch["created_by"], watch["notes"]),
                )
            for alert in bundle.get("monitoring_alerts", []):
                connection.execute(
                    "INSERT INTO monitoring_alerts(alert_id,case_id,watch_id,snapshot_id,comparison_id,alert_type,severity,title,body,status,created_at,acknowledged_at,acknowledged_by,resolved_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (alert["alert_id"], alert["case_id"], alert["watch_id"], alert["snapshot_id"], alert["comparison_id"], alert["alert_type"], alert["severity"], alert["title"], alert["body"], alert["status"], alert["created_at"], alert["acknowledged_at"], alert["acknowledged_by"], alert["resolved_at"], _json_dump(alert["metadata"])),
                )
            for handoff in bundle.get("site_intelligence_events", []):
                connection.execute(
                    "INSERT INTO site_intelligence_events(event_id,case_id,event_type,observed_at,handoff_json,handoff_sha256,ingested_at) VALUES(?,?,?,?,?,?,?)",
                    (handoff["event_id"], handoff["case_id"], handoff["event_type"], handoff["observed_at"], _json_dump(handoff), sha256_digest(handoff), bundle["exported_at"]),
                )
            for actor in bundle.get("stakeholder_actors", []):
                connection.execute("INSERT INTO stakeholder_actors(actor_id,case_id,actor_json,created_at) VALUES(?,?,?,?)", (actor["actor_id"], actor["case_id"], _json_dump(actor), actor["created_at"]))
            for relationship in bundle.get("stakeholder_relationships", []):
                connection.execute("INSERT INTO stakeholder_relationships(relationship_id,case_id,source_actor_id,target_actor_id,relationship_json,created_at) VALUES(?,?,?,?,?,?)", (relationship["relationship_id"], relationship["case_id"], relationship["source_actor_id"], relationship["target_actor_id"], _json_dump(relationship), relationship["created_at"]))
            for incentive in bundle.get("stakeholder_incentives", []):
                connection.execute("INSERT INTO stakeholder_incentives(incentive_id,case_id,actor_id,incentive_json,created_at) VALUES(?,?,?,?,?)", (incentive["incentive_id"], incentive["case_id"], incentive["actor_id"], _json_dump(incentive), incentive["created_at"]))
            for pressure in bundle.get("stakeholder_pressures", []):
                connection.execute("INSERT INTO stakeholder_pressures(pressure_id,case_id,actor_id,source_actor_id,pressure_json,created_at) VALUES(?,?,?,?,?,?)", (pressure["pressure_id"], pressure["case_id"], pressure["actor_id"], pressure["source_actor_id"], _json_dump(pressure), pressure["created_at"]))
            for consequence in bundle.get("stakeholder_consequences", []):
                connection.execute("INSERT INTO stakeholder_consequences(consequence_id,case_id,actor_id,consequence_json,created_at) VALUES(?,?,?,?,?)", (consequence["consequence_id"], consequence["case_id"], consequence["actor_id"], _json_dump(consequence), consequence["created_at"]))
            for handoff in bundle.get("catalyst_canvas_handoffs", []):
                connection.execute("INSERT INTO catalyst_canvas_handoffs(handoff_id,case_id,canvas_id,handoff_json,handoff_sha256,imported_at) VALUES(?,?,?,?,?,?)", (handoff["handoff_id"], handoff["case_id"], handoff["canvas_id"], _json_dump(handoff["handoff"]), handoff["handoff_sha256"], handoff["imported_at"]))
            for comparison in bundle.get("comparison_sets", []):
                connection.execute("INSERT INTO comparison_sets(comparison_id,case_id,comparison_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?)", (comparison["comparison_id"], comparison["case_id"], _json_dump(comparison), comparison["status"], comparison["created_at"], comparison["updated_at"]))
            for matrix in bundle.get("comparative_evidence_matrices", []):
                connection.execute("INSERT INTO comparative_evidence_matrices(matrix_id,comparison_id,case_id,matrix_json,matrix_sha256,generated_at) VALUES(?,?,?,?,?,?)", (matrix["matrix_id"], matrix["comparison_id"], matrix["case_id"], _json_dump(matrix), matrix["matrix_sha256"], matrix["generated_at"]))
            for scenario in bundle.get("scenarios", []):
                connection.execute("INSERT INTO scenarios(scenario_id,comparison_id,case_id,scenario_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (scenario["scenario_id"], scenario["comparison_id"], scenario["case_id"], _json_dump(scenario), scenario["status"], scenario["created_at"], scenario["updated_at"]))
            for result in bundle.get("scenario_results", []):
                connection.execute("INSERT INTO scenario_results(result_id,scenario_id,comparison_id,case_id,result_json,result_sha256,generated_at) VALUES(?,?,?,?,?,?,?)", (result["result_id"], result["scenario_id"], result["comparison_id"], result["case_id"], _json_dump(result), result["result_sha256"], result["generated_at"]))
            for analysis in bundle.get("sensitivity_analyses", []):
                connection.execute("INSERT INTO sensitivity_analyses(analysis_id,comparison_id,case_id,analysis_json,analysis_sha256,generated_at) VALUES(?,?,?,?,?,?)", (analysis["analysis_id"], analysis["comparison_id"], analysis["case_id"], _json_dump(analysis), analysis["analysis_sha256"], analysis["generated_at"]))
            for handoff in bundle.get("decision_studio_handoffs", []):
                connection.execute("INSERT INTO decision_studio_handoffs(handoff_id,comparison_id,case_id,handoff_json,handoff_sha256,generated_at) VALUES(?,?,?,?,?,?)", (handoff["handoff_id"], handoff["comparison_id"], handoff["case_id"], _json_dump(handoff), handoff["handoff_sha256"], handoff["generated_at"]))
            for briefing in bundle.get("publication_briefings", []):
                connection.execute("INSERT INTO publication_briefings(briefing_id,case_id,revision_id,briefing_json,briefing_sha256,classification,audience,generated_at) VALUES(?,?,?,?,?,?,?,?)", (briefing["briefing_id"],briefing["case_id"],briefing["revision_id"],_json_dump(briefing),briefing["briefing_sha256"],briefing["classification"],briefing["audience"],briefing["generated_at"]))
            for package in bundle.get("publication_packages", []):
                connection.execute("INSERT INTO publication_packages(package_id,case_id,briefing_id,package_json,package_sha256,status,slug,package_version,idempotency_key,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (package["package_id"],package["case_id"],package["briefing_id"],_json_dump(package),package["package_sha256"],package["status"],package["slug"],package["package_version"],package.get("idempotency_key"),package["generated_at"]))
            for embed in bundle.get("public_embeds", []):
                connection.execute("INSERT INTO public_embeds(embed_id,case_id,package_id,embed_json,embed_sha256,slug,status,created_at) VALUES(?,?,?,?,?,?,?,?)", (embed["embed_id"],embed["case_id"],embed["package_id"],_json_dump(embed),embed["embed_sha256"],embed["slug"],embed["status"],embed["created_at"]))
            for handoff in bundle.get("platform_handoffs", []):
                connection.execute("INSERT INTO platform_handoffs(handoff_id,case_id,package_id,target,handoff_json,handoff_sha256,generated_at) VALUES(?,?,?,?,?,?,?)", (handoff["handoff_id"],handoff["case_id"],handoff["package_id"],handoff["target"],_json_dump(handoff),handoff["handoff_sha256"],handoff["generated_at"]))
            for assessment in bundle.get("retention_assessments", []):
                connection.execute("INSERT INTO retention_assessments(assessment_id,case_id,policy_id,assessment_json,assessment_sha256,status,assessed_at) VALUES(?,?,?,?,?,?,?)", (assessment["assessment_id"],assessment["case_id"],assessment["policy_id"],_json_dump(assessment),assessment["assessment_sha256"],assessment["status"],assessment["assessed_at"]))
            for dossier in bundle.get("connected_dossiers", []):
                connection.execute("INSERT INTO connected_dossiers(dossier_id,case_id,dossier_json,dossier_sha256,generated_at) VALUES(?,?,?,?,?)", (dossier["dossier_id"],dossier["case_id"],_json_dump(dossier),dossier["dossier_sha256"],dossier["generated_at"]))
            for event in bundle.get("platform_events", []):
                connection.execute("INSERT INTO platform_events(event_id,case_id,source_module,event_type,idempotency_key,event_json,event_sha256,occurred_at) VALUES(?,?,?,?,?,?,?,?)", (event["event_id"],event["case_id"],event["source_module"],event["event_type"],event["idempotency_key"],_json_dump(event),event["event_sha256"],event["occurred_at"]))
            for route in bundle.get("integration_routes", []):
                connection.execute("INSERT INTO integration_routes(route_id,case_id,source_module,target_module,artifact_type,artifact_id,status,route_json,route_sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (route["route_id"],route["case_id"],route["source_module"],route["target_module"],route["artifact_type"],route["artifact_id"],route["status"],_json_dump(route),route["route_sha256"],route["created_at"]))
            for activity in bundle["activity"]:
                self._activity(
                    connection, activity["case_id"], activity["event_type"], entity_id=activity["entity_id"],
                    payload=activity["payload"], created_at=activity["created_at"], activity_id=activity["activity_id"],
                )
        imported = self.get_case(case_id, include_details=True)
        return {"case": imported, "verification": report}

    # ------------------------------------------------------------------
    # v2.0.0 connected institutional platform

    def ingest_platform_event(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        event = normalize_platform_event(payload)
        if event["case_id"] is not None:
            self.get_case(event["case_id"])
        existing = self._connection.execute("SELECT event_json FROM platform_events WHERE idempotency_key=?", (event["idempotency_key"],)).fetchone()
        if existing:
            current = _json_load(existing["event_json"])
            if current["event_sha256"] != event["event_sha256"]:
                raise NarrativeRiskValidationError("idempotency_key already exists with different platform-event content")
            return current
        with self._transaction() as connection:
            connection.execute("INSERT INTO platform_events(event_id,case_id,source_module,event_type,idempotency_key,event_json,event_sha256,occurred_at) VALUES(?,?,?,?,?,?,?,?)", (event["event_id"],event["case_id"],event["source_module"],event["event_type"],event["idempotency_key"],_json_dump(event),event["event_sha256"],event["occurred_at"]))
            if event["case_id"] is not None:
                self._activity(connection,event["case_id"],"platform_event",entity_id=event["event_id"],payload={"source_module":event["source_module"],"event_type":event["event_type"]},created_at=event["occurred_at"])
        return event

    def list_platform_events(self, *, case_id: str | None = None, source_module: str | None = None) -> List[Dict[str, Any]]:
        clauses=[]; params=[]
        if case_id is not None: clauses.append("case_id=?"); params.append(case_id)
        if source_module is not None: clauses.append("source_module=?"); params.append(source_module)
        sql="SELECT event_json FROM platform_events"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY occurred_at,event_id"
        return [_json_load(row["event_json"]) for row in self._connection.execute(sql,params).fetchall()]

    def create_integration_route(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        route = build_integration_route(payload)
        self.get_case(route["case_id"])
        with self._transaction() as connection:
            connection.execute("INSERT INTO integration_routes(route_id,case_id,source_module,target_module,artifact_type,artifact_id,status,route_json,route_sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (route["route_id"],route["case_id"],route["source_module"],route["target_module"],route["artifact_type"],route["artifact_id"],route["status"],_json_dump(route),route["route_sha256"],route["created_at"]))
            self._activity(connection,route["case_id"],"integration_route",entity_id=route["route_id"],payload={"source_module":route["source_module"],"target_module":route["target_module"],"status":route["status"]},created_at=route["created_at"])
        return route

    def list_integration_routes(self, *, case_id: str | None = None, source_module: str | None = None, target_module: str | None = None) -> List[Dict[str, Any]]:
        clauses=[]; params=[]
        for column,value in (("case_id",case_id),("source_module",source_module),("target_module",target_module)):
            if value is not None: clauses.append(f"{column}=?"); params.append(value)
        sql="SELECT route_json FROM integration_routes"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY created_at,route_id"
        return [_json_load(row["route_json"]) for row in self._connection.execute(sql,params).fetchall()]

    def create_connected_dossier(self, case_id: str, *, generated_at: str | None = None, dossier_id: str | None = None) -> Dict[str, Any]:
        case=self.get_case(case_id)
        revisions=self.list_revisions(case_id)
        latest=revisions[-1] if revisions else None
        dossier=build_connected_dossier(case=case,latest_revision=latest,governance=self.get_case_governance_workflow(case_id),alerts=self.list_monitoring_alerts(case_id=case_id),stakeholder_intelligence=self.get_stakeholder_intelligence(case_id,generated_at=generated_at or case["updated_at"]),comparative_portfolio=self.get_comparative_portfolio(case_id,generated_at=generated_at or case["updated_at"]),publication_packages=self.list_publication_packages(case_id),platform_handoffs=self.list_platform_handoffs(case_id),retention_assessments=self.list_retention_assessments(case_id),platform_events=self.list_platform_events(case_id=case_id),integration_routes=self.list_integration_routes(case_id=case_id),generated_at=generated_at,dossier_id=dossier_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO connected_dossiers(dossier_id,case_id,dossier_json,dossier_sha256,generated_at) VALUES(?,?,?,?,?)", (dossier["dossier_id"],case_id,_json_dump(dossier),dossier["dossier_sha256"],dossier["generated_at"]))
            self._activity(connection,case_id,"connected_dossier",entity_id=dossier["dossier_id"],payload={"dossier_sha256":dossier["dossier_sha256"]},created_at=dossier["generated_at"])
        return dossier

    def list_connected_dossiers(self, case_id: str) -> List[Dict[str, Any]]:
        return [_json_load(row["dossier_json"]) for row in self._connection.execute("SELECT dossier_json FROM connected_dossiers WHERE case_id=? ORDER BY generated_at,dossier_id",(case_id,)).fetchall()]

    def create_institutional_workspace(self, organization_id: str, *, generated_at: str | None = None, workspace_id: str | None = None) -> Dict[str, Any]:
        cases=self.list_cases(organization_id=organization_id,archived=None,limit=1000)
        case_ids={item["case_id"] for item in cases}
        dossiers=[item for case_id in case_ids for item in self.list_connected_dossiers(case_id)]
        events=[item for item in self.list_platform_events() if item.get("case_id") in case_ids]
        routes=[item for item in self.list_integration_routes() if item.get("case_id") in case_ids]
        workspace=build_institutional_workspace(organization_id=organization_id,cases=cases,dossiers=dossiers,platform_events=events,integration_routes=routes,generated_at=generated_at,workspace_id=workspace_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO institutional_workspaces(workspace_id,organization_id,workspace_json,workspace_sha256,generated_at) VALUES(?,?,?,?,?)", (workspace["workspace_id"],organization_id,_json_dump(workspace),workspace["workspace_sha256"],workspace["generated_at"]))
        return workspace

    def list_institutional_workspaces(self, organization_id: str) -> List[Dict[str, Any]]:
        return [_json_load(row["workspace_json"]) for row in self._connection.execute("SELECT workspace_json FROM institutional_workspaces WHERE organization_id=? ORDER BY generated_at,workspace_id",(organization_id,)).fetchall()]

    # ------------------------------------------------------------------
    # v2.0.0 stakeholder, incentive, and pressure intelligence

    def _ensure_actor(self, actor_id: str, case_id: str) -> None:
        row = self._connection.execute("SELECT case_id FROM stakeholder_actors WHERE actor_id=?", (actor_id,)).fetchone()
        if row is None: raise NarrativeRiskValidationError(f"stakeholder actor not found: {actor_id}")
        if row["case_id"] != case_id: raise NarrativeRiskValidationError("stakeholder actor belongs to another case")

    def add_stakeholder_actor(self, case_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        case = self.get_case(case_id); actor = normalize_actor(payload, case_id=case["case_id"])
        with self._transaction() as connection:
            try: connection.execute("INSERT INTO stakeholder_actors(actor_id,case_id,actor_json,created_at) VALUES(?,?,?,?)", (actor["actor_id"], actor["case_id"], _json_dump(actor), actor["created_at"]))
            except sqlite3.IntegrityError as exc: raise NarrativeRiskValidationError(f"stakeholder actor already exists: {actor['actor_id']}") from exc
            self._activity(connection, case["case_id"], "stakeholder_actor_added", entity_id=actor["actor_id"], payload={"name": actor["name"], "actor_type": actor["actor_type"]}, created_at=actor["created_at"])
        return actor

    def list_stakeholder_actors(self, case_id: str) -> List[Dict[str, Any]]:
        rows=self._connection.execute("SELECT actor_json FROM stakeholder_actors WHERE case_id=? ORDER BY created_at,actor_id", (case_id,)).fetchall(); return [_json_load(r["actor_json"]) for r in rows]

    def add_stakeholder_relationship(self, case_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self.get_case(case_id); item=normalize_relationship(payload,case_id=case_id); self._ensure_actor(item["source_actor_id"],case_id); self._ensure_actor(item["target_actor_id"],case_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO stakeholder_relationships(relationship_id,case_id,source_actor_id,target_actor_id,relationship_json,created_at) VALUES(?,?,?,?,?,?)", (item["relationship_id"],case_id,item["source_actor_id"],item["target_actor_id"],_json_dump(item),item["created_at"]))
            self._activity(connection,case_id,"stakeholder_relationship_added",entity_id=item["relationship_id"],payload={"relationship_type":item["relationship_type"]},created_at=item["created_at"])
        return item

    def list_stakeholder_relationships(self, case_id: str) -> List[Dict[str, Any]]:
        rows=self._connection.execute("SELECT relationship_json FROM stakeholder_relationships WHERE case_id=? ORDER BY created_at,relationship_id",(case_id,)).fetchall(); return [_json_load(r["relationship_json"]) for r in rows]

    def add_stakeholder_incentive(self, case_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self.get_case(case_id); item=normalize_incentive(payload,case_id=case_id); self._ensure_actor(item["actor_id"],case_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO stakeholder_incentives(incentive_id,case_id,actor_id,incentive_json,created_at) VALUES(?,?,?,?,?)",(item["incentive_id"],case_id,item["actor_id"],_json_dump(item),item["created_at"]))
            self._activity(connection,case_id,"stakeholder_incentive_added",entity_id=item["incentive_id"],payload={"incentive_type":item["incentive_type"],"conflict_status":item["conflict_status"]},created_at=item["created_at"])
        return item

    def list_stakeholder_incentives(self, case_id: str) -> List[Dict[str, Any]]:
        rows=self._connection.execute("SELECT incentive_json FROM stakeholder_incentives WHERE case_id=? ORDER BY created_at,incentive_id",(case_id,)).fetchall(); return [_json_load(r["incentive_json"]) for r in rows]

    def add_stakeholder_pressure(self, case_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self.get_case(case_id); item=normalize_pressure(payload,case_id=case_id); self._ensure_actor(item["actor_id"],case_id)
        if item["source_actor_id"]: self._ensure_actor(item["source_actor_id"],case_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO stakeholder_pressures(pressure_id,case_id,actor_id,source_actor_id,pressure_json,created_at) VALUES(?,?,?,?,?,?)",(item["pressure_id"],case_id,item["actor_id"],item["source_actor_id"],_json_dump(item),item["created_at"]))
            self._activity(connection,case_id,"stakeholder_pressure_added",entity_id=item["pressure_id"],payload={"pressure_type":item["pressure_type"],"intensity":item["intensity"]},created_at=item["created_at"])
        return item

    def list_stakeholder_pressures(self, case_id: str) -> List[Dict[str, Any]]:
        rows=self._connection.execute("SELECT pressure_json FROM stakeholder_pressures WHERE case_id=? ORDER BY created_at,pressure_id",(case_id,)).fetchall(); return [_json_load(r["pressure_json"]) for r in rows]

    def add_stakeholder_consequence(self, case_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self.get_case(case_id); item=normalize_consequence(payload,case_id=case_id); self._ensure_actor(item["actor_id"],case_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO stakeholder_consequences(consequence_id,case_id,actor_id,consequence_json,created_at) VALUES(?,?,?,?,?)",(item["consequence_id"],case_id,item["actor_id"],_json_dump(item),item["created_at"]))
            self._activity(connection,case_id,"stakeholder_consequence_added",entity_id=item["consequence_id"],payload={"impact_type":item["impact_type"],"direction":item["direction"],"severity":item["severity"]},created_at=item["created_at"])
        return item

    def list_stakeholder_consequences(self, case_id: str) -> List[Dict[str, Any]]:
        rows=self._connection.execute("SELECT consequence_json FROM stakeholder_consequences WHERE case_id=? ORDER BY created_at,consequence_id",(case_id,)).fetchall(); return [_json_load(r["consequence_json"]) for r in rows]

    def get_stakeholder_intelligence(self, case_id: str, *, generated_at: str | None = None) -> Dict[str, Any]:
        normalized_case_id = _urn_uuid(case_id, "case_id")
        row = self._connection.execute("SELECT updated_at FROM cases WHERE case_id=?", (normalized_case_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"case not found: {normalized_case_id}")
        return build_stakeholder_intelligence(case_id=normalized_case_id,actors=self.list_stakeholder_actors(normalized_case_id),relationships=self.list_stakeholder_relationships(normalized_case_id),incentives=self.list_stakeholder_incentives(normalized_case_id),pressures=self.list_stakeholder_pressures(normalized_case_id),consequences=self.list_stakeholder_consequences(normalized_case_id),generated_at=generated_at or row["updated_at"])

    def import_catalyst_canvas_stakeholders(self, case_id: str, payload: Mapping[str, Any], *, imported_at: str | None = None) -> Dict[str, Any]:
        self.get_case(case_id); handoff=validate_canvas_handoff(payload); timestamp=_validate_datetime(imported_at,"imported_at") if imported_at else _iso_now(); ids={}
        canvas_ids = {item["canvas_stakeholder_id"] for item in handoff["stakeholders"]}
        for index, relationship in enumerate(handoff.get("relationships", [])):
            for field in ("source_canvas_stakeholder_id", "target_canvas_stakeholder_id"):
                if relationship[field] not in canvas_ids:
                    raise NarrativeRiskValidationError(f"relationships[{index}].{field} does not reference a handoff stakeholder")
        actors=[]
        for raw in handoff["stakeholders"]:
            actor_payload=dict(raw); external=actor_payload.pop("canvas_stakeholder_id"); actor_payload["external_id"]=f"catalyst-canvas:{handoff['canvas_id']}:{external}"; actor_payload["created_at"]=timestamp
            actor=self.add_stakeholder_actor(case_id,actor_payload); ids[external]=actor["actor_id"]; actors.append(actor)
        relationships=[]
        for raw in handoff.get("relationships",[]):
            rel={"source_actor_id":ids[raw["source_canvas_stakeholder_id"]],"target_actor_id":ids[raw["target_canvas_stakeholder_id"]],"relationship_type":raw["relationship_type"],"strength":raw.get("strength","unknown"),"description":raw.get("description","") ,"created_at":timestamp}
            relationships.append(self.add_stakeholder_relationship(case_id,rel))
        handoff_id=_urn_uuid(None,"handoff_id"); stored={"handoff_id":handoff_id,"case_id":case_id,"canvas_id":handoff["canvas_id"],"handoff":handoff,"handoff_sha256":sha256_digest(handoff),"imported_at":timestamp}
        with self._transaction() as connection:
            connection.execute("INSERT INTO catalyst_canvas_handoffs(handoff_id,case_id,canvas_id,handoff_json,handoff_sha256,imported_at) VALUES(?,?,?,?,?,?)",(handoff_id,case_id,handoff["canvas_id"],_json_dump(handoff),stored["handoff_sha256"],timestamp))
            self._activity(connection,case_id,"catalyst_canvas_stakeholders_imported",entity_id=handoff_id,payload={"canvas_id":handoff["canvas_id"],"actor_count":len(actors),"relationship_count":len(relationships)},created_at=timestamp)
        return {"handoff":stored,"actors":actors,"relationships":relationships,"intelligence":self.get_stakeholder_intelligence(case_id,generated_at=timestamp)}

    def list_canvas_handoffs(self, case_id: str) -> List[Dict[str, Any]]:
        rows=self._connection.execute("SELECT * FROM catalyst_canvas_handoffs WHERE case_id=? ORDER BY imported_at,handoff_id",(case_id,)).fetchall(); return [{"handoff_id":r["handoff_id"],"case_id":r["case_id"],"canvas_id":r["canvas_id"],"handoff":_json_load(r["handoff_json"]),"handoff_sha256":r["handoff_sha256"],"imported_at":r["imported_at"]} for r in rows]

    # ------------------------------------------------------------------
    # v2.0.0 comparative narratives and scenario analysis

    def _records_for_comparison(self, comparison: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}
        for member in comparison["members"]:
            if member.get("revision_id"):
                revision = self.get_revision(member["revision_id"])
                if revision["case_id"] != comparison["case_id"]:
                    raise NarrativeRiskValidationError("comparison revision belongs to another case")
                record = revision["record"]
            else:
                with self._lock:
                    row = self._connection.execute(
                        "SELECT record_json, case_id FROM revisions WHERE record_id=?", (member["record_id"],)
                    ).fetchone()
                if row is None:
                    raise NarrativeRiskValidationError(f"comparison record not found: {member['record_id']}")
                if row["case_id"] != comparison["case_id"]:
                    raise NarrativeRiskValidationError("comparison record belongs to another case")
                record = _json_load(row["record_json"])
            if record["identifiers"]["record_id"] != member["record_id"]:
                raise NarrativeRiskValidationError("comparison member record_id does not match its revision")
            records[member["record_id"]] = record
        return records

    def create_comparison_set(self, case_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        case = self.get_case(case_id)
        comparison = normalize_comparison_set(payload, case_id=case["case_id"])
        self._records_for_comparison(comparison)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO comparison_sets(comparison_id, case_id, comparison_json, status, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                    (comparison["comparison_id"], comparison["case_id"], _json_dump(comparison), comparison["status"], comparison["created_at"], comparison["updated_at"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"comparison set already exists: {comparison['comparison_id']}") from exc
            self._activity(connection, case["case_id"], "comparison_set_created", entity_id=comparison["comparison_id"], payload={"title": comparison["title"], "member_count": len(comparison["members"])}, created_at=comparison["created_at"])
        return comparison

    def get_comparison_set(self, comparison_id: str) -> Dict[str, Any]:
        normalized = comparison_urn(comparison_id, "comparison_id")
        with self._lock:
            row = self._connection.execute("SELECT comparison_json FROM comparison_sets WHERE comparison_id=?", (normalized,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"comparison set not found: {normalized}")
        value = _json_load(row["comparison_json"])
        _schema_error("comparison set", value, COMPARISON_SET_SCHEMA_PATH)
        return value

    def list_comparison_sets(self, *, case_id: str | None = None, status: str | None = None) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if case_id:
            clauses.append("case_id=?"); params.append(_urn_uuid(case_id, "case_id"))
        if status:
            clauses.append("status=?"); params.append(status)
        sql = "SELECT comparison_json FROM comparison_sets" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY updated_at, comparison_id"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        values = [_json_load(row["comparison_json"]) for row in rows]
        for value in values: _schema_error("comparison set", value, COMPARISON_SET_SCHEMA_PATH)
        return values

    def generate_comparative_evidence_matrix(self, comparison_id: str, *, generated_at: str | None = None) -> Dict[str, Any]:
        comparison = self.get_comparison_set(comparison_id)
        records = self._records_for_comparison(comparison)
        matrix = build_evidence_matrix(comparison, records, generated_at=generated_at)
        with self._transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO comparative_evidence_matrices(matrix_id, comparison_id, case_id, matrix_json, matrix_sha256, generated_at) VALUES(?,?,?,?,?,?)",
                (matrix["matrix_id"], matrix["comparison_id"], matrix["case_id"], _json_dump(matrix), matrix["matrix_sha256"], matrix["generated_at"]),
            )
            self._activity(connection, matrix["case_id"], "comparative_evidence_matrix_generated", entity_id=matrix["matrix_id"], payload=matrix["summary"], created_at=matrix["generated_at"])
        return matrix

    def list_comparative_evidence_matrices(self, comparison_id: str) -> List[Dict[str, Any]]:
        comparison = self.get_comparison_set(comparison_id)
        with self._lock:
            rows = self._connection.execute("SELECT matrix_json FROM comparative_evidence_matrices WHERE comparison_id=? ORDER BY generated_at, matrix_id", (comparison["comparison_id"],)).fetchall()
        values = [_json_load(row["matrix_json"]) for row in rows]
        for value in values: _schema_error("comparative evidence matrix", value, COMPARATIVE_EVIDENCE_MATRIX_SCHEMA_PATH)
        return values

    def create_scenario(self, comparison_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        comparison = self.get_comparison_set(comparison_id)
        scenario = normalize_scenario(payload, comparison_id=comparison["comparison_id"], case_id=comparison["case_id"])
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO scenarios(scenario_id, comparison_id, case_id, scenario_json, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                    (scenario["scenario_id"], scenario["comparison_id"], scenario["case_id"], _json_dump(scenario), scenario["status"], scenario["created_at"], scenario["updated_at"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"scenario already exists: {scenario['scenario_id']}") from exc
            self._activity(connection, scenario["case_id"], "scenario_created", entity_id=scenario["scenario_id"], payload={"name": scenario["name"], "scenario_type": scenario["scenario_type"]}, created_at=scenario["created_at"])
        return scenario

    def get_scenario(self, scenario_id: str) -> Dict[str, Any]:
        normalized = comparison_urn(scenario_id, "scenario_id")
        with self._lock:
            row = self._connection.execute("SELECT scenario_json FROM scenarios WHERE scenario_id=?", (normalized,)).fetchone()
        if row is None: raise NarrativeRiskValidationError(f"scenario not found: {normalized}")
        value = _json_load(row["scenario_json"]); _schema_error("scenario", value, SCENARIO_SCHEMA_PATH); return value

    def list_scenarios(self, *, comparison_id: str | None = None, case_id: str | None = None, status: str | None = None) -> List[Dict[str, Any]]:
        clauses=[]; params=[]
        if comparison_id: clauses.append("comparison_id=?"); params.append(comparison_urn(comparison_id, "comparison_id"))
        if case_id: clauses.append("case_id=?"); params.append(_urn_uuid(case_id, "case_id"))
        if status: clauses.append("status=?"); params.append(status)
        sql="SELECT scenario_json FROM scenarios"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY created_at, scenario_id"
        with self._lock: rows=self._connection.execute(sql,params).fetchall()
        values=[_json_load(r["scenario_json"]) for r in rows]
        for value in values: _schema_error("scenario",value,SCENARIO_SCHEMA_PATH)
        return values

    def evaluate_scenario(self, scenario_id: str, *, generated_at: str | None = None) -> Dict[str, Any]:
        scenario = self.get_scenario(scenario_id)
        comparison = self.get_comparison_set(scenario["comparison_id"])
        records = self._records_for_comparison(comparison)
        result = evaluate_scenario(scenario, comparison, records, generated_at=generated_at)
        evaluated = dict(scenario); evaluated["status"]="evaluated"; evaluated["updated_at"]=result["generated_at"]
        with self._transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO scenario_results(result_id, scenario_id, comparison_id, case_id, result_json, result_sha256, generated_at) VALUES(?,?,?,?,?,?,?)",
                (result["result_id"], result["scenario_id"], result["comparison_id"], result["case_id"], _json_dump(result), result["result_sha256"], result["generated_at"]),
            )
            connection.execute("UPDATE scenarios SET scenario_json=?, status='evaluated', updated_at=? WHERE scenario_id=?", (_json_dump(evaluated), result["generated_at"], scenario["scenario_id"]))
            self._activity(connection, result["case_id"], "scenario_evaluated", entity_id=result["result_id"], payload={"scenario_id": result["scenario_id"], "risk_score_delta": result["deltas"]["risk_score"]}, created_at=result["generated_at"])
        return result

    def list_scenario_results(self, *, comparison_id: str | None = None, case_id: str | None = None) -> List[Dict[str, Any]]:
        clauses=[]; params=[]
        if comparison_id: clauses.append("comparison_id=?"); params.append(comparison_urn(comparison_id,"comparison_id"))
        if case_id: clauses.append("case_id=?"); params.append(_urn_uuid(case_id,"case_id"))
        sql="SELECT result_json FROM scenario_results"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY generated_at, result_id"
        with self._lock: rows=self._connection.execute(sql,params).fetchall()
        values=[_json_load(r["result_json"]) for r in rows]
        for value in values: _schema_error("scenario result",value,SCENARIO_RESULT_SCHEMA_PATH)
        return values

    def run_comparative_sensitivity(self, comparison_id: str, *, dimensions: Sequence[str] | None = None, generated_at: str | None = None) -> Dict[str, Any]:
        comparison=self.get_comparison_set(comparison_id); records=self._records_for_comparison(comparison)
        analysis=run_sensitivity_analysis(comparison,records,dimensions=dimensions,generated_at=generated_at)
        with self._transaction() as connection:
            connection.execute("INSERT OR REPLACE INTO sensitivity_analyses(analysis_id,comparison_id,case_id,analysis_json,analysis_sha256,generated_at) VALUES(?,?,?,?,?,?)",(analysis["analysis_id"],analysis["comparison_id"],analysis["case_id"],_json_dump(analysis),analysis["analysis_sha256"],analysis["generated_at"]))
            self._activity(connection,analysis["case_id"],"sensitivity_analysis_run",entity_id=analysis["analysis_id"],payload={"dimensions":analysis["dimensions"],"top_driver":analysis["drivers"][0]["dimension"] if analysis["drivers"] else None},created_at=analysis["generated_at"])
        return analysis

    def list_sensitivity_analyses(self, comparison_id: str) -> List[Dict[str, Any]]:
        comparison=self.get_comparison_set(comparison_id)
        with self._lock: rows=self._connection.execute("SELECT analysis_json FROM sensitivity_analyses WHERE comparison_id=? ORDER BY generated_at,analysis_id",(comparison["comparison_id"],)).fetchall()
        values=[_json_load(r["analysis_json"]) for r in rows]
        for value in values: _schema_error("sensitivity analysis",value,SENSITIVITY_ANALYSIS_SCHEMA_PATH)
        return values

    def get_comparative_portfolio(self, case_id: str, *, generated_at: str | None = None) -> Dict[str, Any]:
        case=self.get_case(case_id); comparisons=self.list_comparison_sets(case_id=case["case_id"])
        records={}
        for comparison in comparisons: records.update(self._records_for_comparison(comparison))
        scenarios=self.list_scenarios(case_id=case["case_id"]); results=self.list_scenario_results(case_id=case["case_id"])
        analyses=[]
        for comparison in comparisons: analyses.extend(self.list_sensitivity_analyses(comparison["comparison_id"]))
        governance=self.get_case_governance_workflow(case["case_id"])
        return build_comparative_portfolio(case_id=case["case_id"],comparisons=comparisons,records_by_id=records,scenarios=scenarios,scenario_results=results,sensitivity_analyses=analyses,governance=governance,generated_at=generated_at)

    def create_decision_studio_handoff(self, comparison_id: str, *, selected_scenario_ids: Sequence[str] | None = None, generated_at: str | None = None) -> Dict[str, Any]:
        comparison=self.get_comparison_set(comparison_id)
        matrices=self.list_comparative_evidence_matrices(comparison["comparison_id"])
        results=self.list_scenario_results(comparison_id=comparison["comparison_id"])
        analyses=self.list_sensitivity_analyses(comparison["comparison_id"])
        portfolio=self.get_comparative_portfolio(comparison["case_id"],generated_at=generated_at)
        governance=self.get_case_governance_workflow(comparison["case_id"],include_details=True)
        handoff=build_decision_studio_handoff(comparison=comparison,evidence_matrix=matrices[-1] if matrices else None,scenario_results=results,sensitivity_analysis=analyses[-1] if analyses else None,portfolio=portfolio,governance=governance,selected_scenario_ids=selected_scenario_ids,generated_at=generated_at)
        with self._transaction() as connection:
            connection.execute("INSERT INTO decision_studio_handoffs(handoff_id,comparison_id,case_id,handoff_json,handoff_sha256,generated_at) VALUES(?,?,?,?,?,?)",(handoff["handoff_id"],handoff["comparison_id"],handoff["case_id"],_json_dump(handoff),handoff["handoff_sha256"],handoff["generated_at"]))
            self._activity(connection,handoff["case_id"],"decision_studio_handoff_created",entity_id=handoff["handoff_id"],payload={"comparison_id":handoff["comparison_id"],"scenario_count":len(handoff["scenario_results"])},created_at=handoff["generated_at"])
        return handoff

    def list_decision_studio_handoffs(self, case_id: str) -> List[Dict[str, Any]]:
        normalized=_urn_uuid(case_id,"case_id")
        with self._lock: rows=self._connection.execute("SELECT handoff_json FROM decision_studio_handoffs WHERE case_id=? ORDER BY generated_at,handoff_id",(normalized,)).fetchall()
        values=[_json_load(r["handoff_json"]) for r in rows]
        for value in values: _schema_error("Decision Studio handoff",value,DECISION_STUDIO_HANDOFF_SCHEMA_PATH)
        return values


    # ------------------------------------------------------------------
    # v2.0.0 briefing, publication, API, embed, and platform integration

    def create_publication_briefing(
        self, case_id: str, *, revision_id: str | None = None, audience: str = "internal",
        classification: str = "internal", title: str | None = None, generated_at: str | None = None,
        generated_by: str | None = None, briefing_id: str | None = None,
    ) -> Dict[str, Any]:
        case = self.get_case(case_id)
        revisions = self.list_revisions(case["case_id"])
        if not revisions:
            raise NarrativeRiskValidationError("a publication briefing requires at least one immutable revision")
        revision = self.get_revision(revision_id) if revision_id else revisions[-1]
        if revision["case_id"] != case["case_id"]:
            raise NarrativeRiskValidationError("briefing revision does not belong to the case")
        governance = self.get_case_governance_workflow(case["case_id"], include_details=True, at=generated_at)
        briefing = build_briefing(
            case=case, revision=revision, governance=governance, audience=audience,
            classification=classification, title=title, generated_at=generated_at,
            generated_by=generated_by, briefing_id=briefing_id,
        )
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO publication_briefings(briefing_id,case_id,revision_id,briefing_json,briefing_sha256,classification,audience,generated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (briefing["briefing_id"], briefing["case_id"], briefing["revision_id"], _json_dump(briefing),
                     briefing["briefing_sha256"], briefing["classification"], briefing["audience"], briefing["generated_at"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"publication briefing already exists: {briefing['briefing_id']}") from exc
            self._activity(connection, case["case_id"], "publication_briefing_created", entity_id=briefing["briefing_id"],
                           payload={"classification": briefing["classification"], "audience": briefing["audience"], "public_safe": briefing["public_safe"]},
                           created_at=briefing["generated_at"])
        return briefing

    def get_publication_briefing(self, briefing_id: str) -> Dict[str, Any]:
        normalized = publication_urn(briefing_id, "briefing_id")
        with self._lock:
            row = self._connection.execute("SELECT briefing_json FROM publication_briefings WHERE briefing_id=?", (normalized,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"publication briefing not found: {normalized}")
        value = _json_load(row["briefing_json"])
        _schema_error("publication briefing", value, BRIEFING_SCHEMA_PATH)
        if sha256_digest({k: v for k, v in value.items() if k != "briefing_sha256"}) != value["briefing_sha256"]:
            raise NarrativeRiskValidationError(f"publication briefing hash mismatch: {normalized}")
        return value

    def list_publication_briefings(self, case_id: str) -> List[Dict[str, Any]]:
        normalized = _urn_uuid(case_id, "case_id")
        with self._lock:
            rows = self._connection.execute("SELECT briefing_id FROM publication_briefings WHERE case_id=? ORDER BY generated_at,briefing_id", (normalized,)).fetchall()
        return [self.get_publication_briefing(row["briefing_id"]) for row in rows]

    def create_publication_package(
        self, briefing_id: str, *, formats: Sequence[str] | None = None, slug: str | None = None,
        status: str | None = None, generated_at: str | None = None, generated_by: str | None = None,
        package_id: str | None = None, package_version: int = 1, public_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        if idempotency_key:
            with self._lock:
                existing = self._connection.execute("SELECT package_json FROM publication_packages WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing is not None:
                return _json_load(existing["package_json"])
        briefing = self.get_publication_briefing(briefing_id)
        package = build_publication_package(
            briefing, formats=formats, slug=slug, status=status, generated_at=generated_at,
            generated_by=generated_by, package_id=package_id, package_version=package_version,
            public_url=public_url, idempotency_key=idempotency_key,
        )
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO publication_packages(package_id,case_id,briefing_id,package_json,package_sha256,status,slug,package_version,idempotency_key,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (package["package_id"], package["case_id"], package["briefing_id"], _json_dump(package), package["package_sha256"],
                     package["status"], package["slug"], package["package_version"], package["idempotency_key"], package["generated_at"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError("publication package identifier, slug/version, or idempotency key already exists") from exc
            self._activity(connection, package["case_id"], "publication_package_created", entity_id=package["package_id"],
                           payload={"status": package["status"], "formats": [item["format"] for item in package["artifacts"]], "package_sha256": package["package_sha256"]},
                           created_at=package["generated_at"])
        return package

    def get_publication_package(self, package_id: str) -> Dict[str, Any]:
        normalized = publication_urn(package_id, "package_id")
        with self._lock:
            row = self._connection.execute("SELECT package_json FROM publication_packages WHERE package_id=?", (normalized,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"publication package not found: {normalized}")
        value = _json_load(row["package_json"])
        _schema_error("publication package", value, PUBLICATION_PACKAGE_SCHEMA_PATH)
        if sha256_digest({k: v for k, v in value.items() if k != "package_sha256"}) != value["package_sha256"]:
            raise NarrativeRiskValidationError(f"publication package hash mismatch: {normalized}")
        return value

    def list_publication_packages(self, case_id: str, *, status: str | None = None) -> List[Dict[str, Any]]:
        normalized = _urn_uuid(case_id, "case_id")
        params: list[Any] = [normalized]; sql = "SELECT package_id FROM publication_packages WHERE case_id=?"
        if status:
            sql += " AND status=?"; params.append(status)
        sql += " ORDER BY generated_at,package_id"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        return [self.get_publication_package(row["package_id"]) for row in rows]

    def update_publication_package_status(self, package_id: str, *, status: str, public_url: str | None = None, changed_at: str | None = None) -> Dict[str, Any]:
        package = self.get_publication_package(package_id)
        normalized_status = _choice(status, "status", {"draft", "ready", "published", "revoked", "superseded"}, "draft")
        if normalized_status == "published" and (package["classification"] != "public" or not package["public_safe"]):
            raise NarrativeRiskValidationError("only a public-safe public package can be published")
        package["status"] = normalized_status
        if public_url is not None: package["public_url"] = public_url
        package["package_sha256"] = sha256_digest({k: v for k, v in package.items() if k != "package_sha256"})
        _schema_error("publication package", package, PUBLICATION_PACKAGE_SCHEMA_PATH)
        timestamp = _validate_datetime(changed_at, "changed_at") if changed_at else _iso_now()
        with self._transaction() as connection:
            connection.execute("UPDATE publication_packages SET package_json=?,package_sha256=?,status=? WHERE package_id=?", (_json_dump(package),package["package_sha256"],normalized_status,package["package_id"]))
            self._activity(connection, package["case_id"], "publication_package_status_changed", entity_id=package["package_id"], payload={"status": normalized_status, "public_url": package.get("public_url")}, created_at=timestamp)
        return package

    def get_publication_artifact(self, package_id: str, format_name: str) -> Dict[str, Any]:
        package = self.get_publication_package(package_id)
        artifact = next((item for item in package["artifacts"] if item["format"] == format_name), None)
        if artifact is None:
            raise NarrativeRiskValidationError(f"publication package does not contain format: {format_name}")
        return deepcopy(artifact)

    def create_public_embed(self, package_id: str, **payload: Any) -> Dict[str, Any]:
        package = self.get_publication_package(package_id)
        embed = build_public_embed(package, **payload)
        with self._transaction() as connection:
            try:
                connection.execute("INSERT INTO public_embeds(embed_id,case_id,package_id,embed_json,embed_sha256,slug,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                   (embed["embed_id"],embed["case_id"],embed["package_id"],_json_dump(embed),embed["embed_sha256"],embed["slug"],embed["status"],embed["created_at"]))
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError("public embed identifier or slug already exists") from exc
            self._activity(connection, embed["case_id"], "public_embed_created", entity_id=embed["embed_id"], payload={"slug":embed["slug"],"status":embed["status"]}, created_at=embed["created_at"])
        return embed

    def get_public_embed(self, embed_id_or_slug: str) -> Dict[str, Any]:
        with self._lock:
            if isinstance(embed_id_or_slug,str) and embed_id_or_slug.startswith("urn:uuid:"):
                row=self._connection.execute("SELECT embed_json FROM public_embeds WHERE embed_id=?", (publication_urn(embed_id_or_slug,"embed_id"),)).fetchone()
            else:
                row=self._connection.execute("SELECT embed_json FROM public_embeds WHERE slug=?", (embed_id_or_slug,)).fetchone()
        if row is None: raise NarrativeRiskValidationError(f"public embed not found: {embed_id_or_slug}")
        value=_json_load(row["embed_json"]); _schema_error("public embed",value,PUBLIC_EMBED_SCHEMA_PATH)
        if sha256_digest({k:v for k,v in value.items() if k!="embed_sha256"}) != value["embed_sha256"]: raise NarrativeRiskValidationError("public embed hash mismatch")
        return value

    def list_public_embeds(self, case_id: str) -> List[Dict[str, Any]]:
        normalized=_urn_uuid(case_id,"case_id")
        with self._lock: rows=self._connection.execute("SELECT embed_id FROM public_embeds WHERE case_id=? ORDER BY created_at,embed_id",(normalized,)).fetchall()
        return [self.get_public_embed(row["embed_id"]) for row in rows]

    def create_api_key(self, *, name: str, scopes: Sequence[str], rate_limit_per_minute: int | None = None, expires_at: str | None = None, created_at: str | None = None, created_by: str | None = None, api_key_id: str | None = None) -> Dict[str, Any]:
        record, secret = create_api_key_record(name=name, scopes=scopes, rate_limit_per_minute=rate_limit_per_minute, expires_at=expires_at, created_at=created_at, created_by=created_by, api_key_id=api_key_id)
        with self._transaction() as connection:
            try:
                connection.execute("INSERT INTO api_keys(api_key_id,name,key_prefix,key_sha256,scopes_json,status,rate_limit_per_minute,created_at,expires_at,last_used_at,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                                   (record["api_key_id"],record["name"],record["key_prefix"],record["key_sha256"],_json_dump(record["scopes"]),record["status"],record["rate_limit_per_minute"],record["created_at"],record["expires_at"],record["last_used_at"],record["created_by"]))
            except sqlite3.IntegrityError as exc: raise NarrativeRiskValidationError("API key identifier or prefix already exists") from exc
        return {"api_key": record, "secret": secret}

    def _api_key_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        value={"api_key_id":row["api_key_id"],"name":row["name"],"key_prefix":row["key_prefix"],"key_sha256":row["key_sha256"],"scopes":_json_load(row["scopes_json"]),"status":row["status"],"rate_limit_per_minute":int(row["rate_limit_per_minute"]),"created_at":row["created_at"],"expires_at":row["expires_at"],"last_used_at":row["last_used_at"],"created_by":row["created_by"]}
        _schema_error("API key",value,API_KEY_SCHEMA_PATH); return value

    def list_api_keys(self) -> List[Dict[str, Any]]:
        with self._lock: rows=self._connection.execute("SELECT * FROM api_keys ORDER BY created_at,api_key_id").fetchall()
        return [self._api_key_from_row(row) for row in rows]

    def authenticate_api_key(self, secret: str, required_scope: str, *, used_at: str | None = None) -> Dict[str, Any]:
        digest=__import__('hashlib').sha256(secret.encode()).hexdigest(); timestamp=_validate_datetime(used_at,"used_at") if used_at else _iso_now()
        with self._lock: row=self._connection.execute("SELECT * FROM api_keys WHERE key_sha256=?",(digest,)).fetchone()
        if row is None: raise NarrativeRiskValidationError("invalid API key")
        record=self._api_key_from_row(row); authorize_api_key(record,secret,required_scope,at=timestamp)
        cutoff=(datetime.fromisoformat(timestamp.replace('Z','+00:00'))-timedelta(minutes=1)).isoformat()
        with self._transaction() as connection:
            count=int(connection.execute("SELECT COUNT(*) FROM api_key_usage WHERE api_key_id=? AND used_at>=?",(record["api_key_id"],cutoff)).fetchone()[0])
            if count >= record["rate_limit_per_minute"]: raise NarrativeRiskValidationError("API rate limit exceeded")
            connection.execute("INSERT INTO api_key_usage(api_key_id,used_at) VALUES(?,?)",(record["api_key_id"],timestamp))
            connection.execute("UPDATE api_keys SET last_used_at=? WHERE api_key_id=?",(timestamp,record["api_key_id"]))
        record["last_used_at"]=timestamp; return record

    def revoke_api_key(self, api_key_id: str) -> Dict[str, Any]:
        normalized=publication_urn(api_key_id,"api_key_id")
        with self._transaction() as connection:
            result=connection.execute("UPDATE api_keys SET status='revoked' WHERE api_key_id=?",(normalized,))
            if result.rowcount==0: raise NarrativeRiskValidationError(f"API key not found: {normalized}")
        with self._lock: row=self._connection.execute("SELECT * FROM api_keys WHERE api_key_id=?",(normalized,)).fetchone()
        return self._api_key_from_row(row)

    def create_platform_handoff(self, package_id: str, *, target: str, generated_at: str | None = None, external_reference: str | None = None, handoff_id: str | None = None) -> Dict[str, Any]:
        package=self.get_publication_package(package_id); handoff=build_platform_handoff(package,target=target,generated_at=generated_at,external_reference=external_reference,handoff_id=handoff_id)
        with self._transaction() as connection:
            try: connection.execute("INSERT INTO platform_handoffs(handoff_id,case_id,package_id,target,handoff_json,handoff_sha256,generated_at) VALUES(?,?,?,?,?,?,?)",(handoff["handoff_id"],handoff["case_id"],handoff["package_id"],handoff["target"],_json_dump(handoff),handoff["handoff_sha256"],handoff["generated_at"]))
            except sqlite3.IntegrityError as exc: raise NarrativeRiskValidationError(f"platform handoff already exists: {handoff['handoff_id']}") from exc
            self._activity(connection,handoff["case_id"],"platform_handoff_created",entity_id=handoff["handoff_id"],payload={"target":handoff["target"],"package_id":handoff["package_id"]},created_at=handoff["generated_at"])
        return handoff

    def list_platform_handoffs(self, case_id: str) -> List[Dict[str, Any]]:
        normalized=_urn_uuid(case_id,"case_id")
        with self._lock: rows=self._connection.execute("SELECT handoff_json FROM platform_handoffs WHERE case_id=? ORDER BY generated_at,handoff_id",(normalized,)).fetchall()
        values=[_json_load(row["handoff_json"]) for row in rows]
        for value in values: _schema_error("platform handoff",value,PLATFORM_HANDOFF_SCHEMA_PATH)
        return values

    # ------------------------------------------------------------------
    # v2.0.0 narrative change, freshness, and monitoring

    def _snapshot_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        snapshot = _json_load(row["snapshot_json"])
        _schema_error("monitoring snapshot", snapshot, MONITORING_SNAPSHOT_SCHEMA_PATH)
        return snapshot

    def get_monitoring_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        normalized_id = monitoring_urn_uuid(snapshot_id, "snapshot_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM monitoring_snapshots WHERE snapshot_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"monitoring snapshot not found: {normalized_id}")
        return self._snapshot_from_row(row)

    def list_monitoring_snapshots(self, case_id: str) -> List[Dict[str, Any]]:
        normalized_case = _urn_uuid(case_id, "case_id")
        self.get_case(normalized_case)
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM monitoring_snapshots WHERE case_id=? ORDER BY captured_at, snapshot_id", (normalized_case,)
            ).fetchall()
        return [self._snapshot_from_row(row) for row in rows]

    def capture_monitoring_snapshot(
        self, case_id: str, *, revision_id: str | None = None, captured_at: str | None = None,
        trigger: str = "manual", snapshot_id: str | None = None,
    ) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if revision_id is None:
            revisions = self.list_revisions(case["case_id"])
            if not revisions:
                raise NarrativeRiskValidationError("case has no revision to monitor")
            revision = revisions[-1]
        else:
            revision = self.get_revision(revision_id)
            if revision["case_id"] != case["case_id"]:
                raise NarrativeRiskValidationError("revision does not belong to the monitored case")
        governance = self.get_case_governance_workflow(case["case_id"], at=captured_at) or {}
        snapshot = build_monitoring_snapshot(
            revision["record"], case_id=case["case_id"], revision_id=revision["revision_id"],
            governance=governance, captured_at=captured_at, trigger=trigger, snapshot_id=snapshot_id,
        )
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO monitoring_snapshots(snapshot_id,case_id,revision_id,record_id,captured_at,trigger,snapshot_json,snapshot_sha256) VALUES(?,?,?,?,?,?,?,?)",
                    (snapshot["snapshot_id"], snapshot["case_id"], snapshot["revision_id"], snapshot["record_id"],
                     snapshot["captured_at"], snapshot["trigger"], _json_dump(snapshot), snapshot["snapshot_sha256"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"monitoring snapshot already exists: {snapshot['snapshot_id']}") from exc
            connection.execute("UPDATE cases SET updated_at=? WHERE case_id=?", (snapshot["captured_at"], case["case_id"]))
            self._activity(connection, case["case_id"], "monitoring_snapshot_captured", entity_id=snapshot["snapshot_id"],
                           payload={"revision_id": snapshot["revision_id"], "trigger": snapshot["trigger"], "freshness": snapshot["freshness_report"]["status"]},
                           created_at=snapshot["captured_at"])
        return snapshot

    def _comparison_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        comparison = _json_load(row["comparison_json"])
        _schema_error("monitoring comparison", comparison, MONITORING_COMPARISON_SCHEMA_PATH)
        return comparison

    def get_monitoring_comparison(self, comparison_id: str) -> Dict[str, Any]:
        normalized_id = monitoring_urn_uuid(comparison_id, "comparison_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM monitoring_comparisons WHERE comparison_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"monitoring comparison not found: {normalized_id}")
        return self._comparison_from_row(row)

    def list_monitoring_comparisons(self, case_id: str) -> List[Dict[str, Any]]:
        normalized_case = _urn_uuid(case_id, "case_id")
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM monitoring_comparisons WHERE case_id=? ORDER BY compared_at, comparison_id", (normalized_case,)
            ).fetchall()
        return [self._comparison_from_row(row) for row in rows]

    def compare_snapshots(
        self, from_snapshot_id: str, to_snapshot_id: str, *, compared_at: str | None = None,
        comparison_id: str | None = None,
    ) -> Dict[str, Any]:
        previous = self.get_monitoring_snapshot(from_snapshot_id)
        current = self.get_monitoring_snapshot(to_snapshot_id)
        revision = self.get_revision(current["revision_id"])
        comparison = compare_monitoring_snapshots(
            previous, current, compared_at=compared_at, method_snapshot=revision["record"]["method_snapshot"],
            comparison_id=comparison_id,
        )
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO monitoring_comparisons(comparison_id,case_id,from_snapshot_id,to_snapshot_id,compared_at,materiality_score,severity,comparison_json,comparison_sha256) VALUES(?,?,?,?,?,?,?,?,?)",
                    (comparison["comparison_id"], comparison["case_id"], comparison["from_snapshot_id"], comparison["to_snapshot_id"],
                     comparison["compared_at"], comparison["materiality_score"], comparison["severity"], _json_dump(comparison), comparison["comparison_sha256"]),
                )
            except sqlite3.IntegrityError as exc:
                existing = connection.execute(
                    "SELECT comparison_id FROM monitoring_comparisons WHERE from_snapshot_id=? AND to_snapshot_id=?",
                    (comparison["from_snapshot_id"], comparison["to_snapshot_id"]),
                ).fetchone()
                if existing:
                    return self.get_monitoring_comparison(existing["comparison_id"])
                raise NarrativeRiskValidationError(f"monitoring comparison already exists: {comparison['comparison_id']}") from exc
            self._activity(connection, comparison["case_id"], "monitoring_snapshots_compared", entity_id=comparison["comparison_id"],
                           payload={"materiality_score": comparison["materiality_score"], "severity": comparison["severity"], "material_change": comparison["material_change"]},
                           created_at=comparison["compared_at"])
        return comparison

    def _watch_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        watch = {
            "watch_id": row["watch_id"], "watch_version": VERSION, "case_id": row["case_id"], "name": row["name"],
            "status": row["status"], "cadence": row["cadence"], "trigger_types": _json_load(row["trigger_types_json"]),
            "source_ids": _json_load(row["source_ids_json"]), "created_at": row["created_at"], "updated_at": row["updated_at"],
            "last_checked_at": row["last_checked_at"], "next_check_at": row["next_check_at"], "created_by": row["created_by"], "notes": row["notes"],
        }
        _schema_error("watchlist", watch, WATCHLIST_SCHEMA_PATH)
        return watch

    def create_watchlist(self, case_id: str, **payload: Any) -> Dict[str, Any]:
        self.get_case(case_id)
        watch = normalize_watchlist(payload, case_id=case_id)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO watchlists(watch_id,case_id,name,status,cadence,trigger_types_json,source_ids_json,created_at,updated_at,last_checked_at,next_check_at,created_by,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (watch["watch_id"], watch["case_id"], watch["name"], watch["status"], watch["cadence"], _json_dump(watch["trigger_types"]),
                     _json_dump(watch["source_ids"]), watch["created_at"], watch["updated_at"], watch["last_checked_at"], watch["next_check_at"],
                     watch["created_by"], watch["notes"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"watchlist already exists: {watch['watch_id']}") from exc
            self._activity(connection, watch["case_id"], "watchlist_created", entity_id=watch["watch_id"],
                           payload={"name": watch["name"], "cadence": watch["cadence"], "trigger_types": watch["trigger_types"]}, created_at=watch["created_at"])
        return self.get_watchlist(watch["watch_id"])

    def get_watchlist(self, watch_id: str) -> Dict[str, Any]:
        normalized_id = monitoring_urn_uuid(watch_id, "watch_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM watchlists WHERE watch_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"watchlist not found: {normalized_id}")
        return self._watch_from_row(row)

    def list_watchlists(self, *, case_id: str | None = None, status: str | None = None, due_at: str | None = None) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if case_id is not None:
            clauses.append("case_id=?"); params.append(_urn_uuid(case_id, "case_id"))
        if status is not None:
            normalized_status = _choice(status, "status", WATCH_STATUSES, "active")
            clauses.append("status=?"); params.append(normalized_status)
        if due_at is not None:
            timestamp = monitoring_datetime(due_at, "due_at")
            clauses.append("next_check_at IS NOT NULL AND next_check_at<=?"); params.append(timestamp)
        sql = "SELECT * FROM watchlists" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY next_check_at, created_at"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        return [self._watch_from_row(row) for row in rows]

    def update_watchlist(self, watch_id: str, changes: Mapping[str, Any]) -> Dict[str, Any]:
        watch = self.get_watchlist(watch_id)
        allowed = {"name", "status", "cadence", "trigger_types", "source_ids", "next_check_at", "notes", "updated_at"}
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise NarrativeRiskValidationError(f"unsupported watchlist update field(s): {', '.join(unknown)}")
        payload = dict(watch)
        payload.update(changes)
        payload.pop("watch_version", None)
        normalized = normalize_watchlist(payload, case_id=watch["case_id"])
        with self._transaction() as connection:
            connection.execute(
                "UPDATE watchlists SET name=?,status=?,cadence=?,trigger_types_json=?,source_ids_json=?,updated_at=?,next_check_at=?,notes=? WHERE watch_id=?",
                (normalized["name"], normalized["status"], normalized["cadence"], _json_dump(normalized["trigger_types"]), _json_dump(normalized["source_ids"]),
                 normalized["updated_at"], normalized["next_check_at"], normalized["notes"], watch["watch_id"]),
            )
            self._activity(connection, watch["case_id"], "watchlist_updated", entity_id=watch["watch_id"], payload=dict(changes), created_at=normalized["updated_at"])
        return self.get_watchlist(watch["watch_id"])

    def _alert_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        alert = {
            "alert_id": row["alert_id"], "alert_version": VERSION, "case_id": row["case_id"], "watch_id": row["watch_id"],
            "snapshot_id": row["snapshot_id"], "comparison_id": row["comparison_id"], "alert_type": row["alert_type"],
            "severity": row["severity"], "title": row["title"], "body": row["body"], "status": row["status"], "created_at": row["created_at"],
            "acknowledged_at": row["acknowledged_at"], "acknowledged_by": row["acknowledged_by"], "resolved_at": row["resolved_at"],
            "metadata": _json_load(row["metadata_json"]),
        }
        _schema_error("monitoring alert", alert, MONITORING_ALERT_SCHEMA_PATH)
        return alert

    def create_monitoring_alert(self, **payload: Any) -> Dict[str, Any]:
        alert = build_alert(**payload)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO monitoring_alerts(alert_id,case_id,watch_id,snapshot_id,comparison_id,alert_type,severity,title,body,status,created_at,acknowledged_at,acknowledged_by,resolved_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (alert["alert_id"], alert["case_id"], alert["watch_id"], alert["snapshot_id"], alert["comparison_id"], alert["alert_type"], alert["severity"],
                     alert["title"], alert["body"], alert["status"], alert["created_at"], None, None, None, _json_dump(alert["metadata"])),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"monitoring alert already exists: {alert['alert_id']}") from exc
            self._activity(connection, alert["case_id"], "monitoring_alert_created", entity_id=alert["alert_id"],
                           payload={"alert_type": alert["alert_type"], "severity": alert["severity"]}, created_at=alert["created_at"])
        return self.get_monitoring_alert(alert["alert_id"])

    def get_monitoring_alert(self, alert_id: str) -> Dict[str, Any]:
        normalized_id = monitoring_urn_uuid(alert_id, "alert_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM monitoring_alerts WHERE alert_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"monitoring alert not found: {normalized_id}")
        return self._alert_from_row(row)

    def list_monitoring_alerts(
        self, *, case_id: str | None = None, watch_id: str | None = None, status: str | None = None,
        severity: str | None = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if case_id is not None: clauses.append("case_id=?"); params.append(_urn_uuid(case_id, "case_id"))
        if watch_id is not None: clauses.append("watch_id=?"); params.append(monitoring_urn_uuid(watch_id, "watch_id"))
        if status is not None: clauses.append("status=?"); params.append(_choice(status, "status", ALERT_STATUSES, "open"))
        if severity is not None: clauses.append("severity=?"); params.append(_choice(severity, "severity", ALERT_SEVERITIES, "info"))
        sql = "SELECT * FROM monitoring_alerts" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at DESC, alert_id"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        return [self._alert_from_row(row) for row in rows]

    def update_monitoring_alert_status(
        self, alert_id: str, *, status: str, actor_id: str, changed_at: str | None = None,
    ) -> Dict[str, Any]:
        alert = self.get_monitoring_alert(alert_id)
        normalized_status = _choice(status, "status", ALERT_STATUSES, "acknowledged")
        timestamp = monitoring_datetime(changed_at, "changed_at") if changed_at else _iso_now()
        actor = _text(actor_id, "actor_id", required=True, maximum=500)
        acknowledged_at = timestamp if normalized_status in {"acknowledged", "resolved"} else alert["acknowledged_at"]
        acknowledged_by = actor if normalized_status in {"acknowledged", "resolved"} else alert["acknowledged_by"]
        resolved_at = timestamp if normalized_status == "resolved" else None
        with self._transaction() as connection:
            connection.execute(
                "UPDATE monitoring_alerts SET status=?,acknowledged_at=?,acknowledged_by=?,resolved_at=? WHERE alert_id=?",
                (normalized_status, acknowledged_at, acknowledged_by, resolved_at, alert["alert_id"]),
            )
            self._activity(connection, alert["case_id"], "monitoring_alert_status_changed", entity_id=alert["alert_id"],
                           payload={"status": normalized_status, "actor_id": actor}, created_at=timestamp)
        return self.get_monitoring_alert(alert["alert_id"])

    @staticmethod
    def _next_watch_check(cadence: str, checked_at: str) -> str | None:
        if cadence == "manual":
            return None
        current = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        delta = {"hourly": timedelta(hours=1), "daily": timedelta(days=1), "weekly": timedelta(days=7), "monthly": timedelta(days=30)}[cadence]
        return (current + delta).isoformat()

    def run_watchlist_check(
        self, watch_id: str, *, revision_id: str | None = None, checked_at: str | None = None,
        trigger: str = "scheduled",
    ) -> Dict[str, Any]:
        watch = self.get_watchlist(watch_id)
        if watch["status"] != "active":
            raise NarrativeRiskValidationError("only active watchlists can be checked")
        timestamp = monitoring_datetime(checked_at, "checked_at") if checked_at else _iso_now()
        previous = self.list_monitoring_snapshots(watch["case_id"])
        snapshot = self.capture_monitoring_snapshot(watch["case_id"], revision_id=revision_id, captured_at=timestamp, trigger=trigger)
        comparison = self.compare_snapshots(previous[-1]["snapshot_id"], snapshot["snapshot_id"], compared_at=timestamp) if previous else None
        generated_alerts: List[Dict[str, Any]] = []

        def emit(alert_type: str, severity: str, title: str, body: str, metadata: Mapping[str, Any] | None = None) -> None:
            if alert_type in watch["trigger_types"]:
                generated_alerts.append(self.create_monitoring_alert(
                    case_id=watch["case_id"], watch_id=watch["watch_id"], snapshot_id=snapshot["snapshot_id"],
                    comparison_id=comparison["comparison_id"] if comparison else None, alert_type=alert_type, severity=severity,
                    title=title, body=body, metadata=metadata or {}, created_at=timestamp,
                ))

        freshness = snapshot["freshness_report"]
        if freshness["counts"]["stale"]:
            emit("source_stale", "high" if freshness["stale_ratio"] >= 0.5 else "medium", "Source freshness requires review",
                 f"{freshness['counts']['stale']} of {freshness['source_count']} monitored sources are stale.", {"freshness_report": freshness})
        if comparison:
            if comparison["material_change"]:
                emit("material_change", comparison["severity"], "Material narrative change detected", " ".join(comparison["reasons"]) or "The monitored case changed materially.", {"comparison": comparison})
            if comparison["evidence_changes"]["added_evidence_ids"]:
                emit("new_evidence", "medium", "New evidence detected", f"{len(comparison['evidence_changes']['added_evidence_ids'])} new evidence item(s) were added.", {"evidence_ids": comparison["evidence_changes"]["added_evidence_ids"]})
            if comparison["evidence_changes"]["content_changed_source_ids"]:
                emit("source_content_changed", "high", "Source content changed", f"{len(comparison['evidence_changes']['content_changed_source_ids'])} source content digest(s) changed.", {"source_ids": comparison["evidence_changes"]["content_changed_source_ids"]})
            if comparison["risk_level_changed"]:
                emit("risk_level_changed", "high", "Risk level changed", f"Risk level changed while monitoring case {watch['case_id']}.", {"comparison_id": comparison["comparison_id"]})
            if comparison["wording_changes"]:
                emit("wording_changed", "medium", "Claim wording changed", f"{len(comparison['wording_changes'])} claim wording change(s) were detected.", {"wording_changes": comparison["wording_changes"]})
            if comparison["confidence_changes"]:
                emit("confidence_changed", "medium", "Confidence state changed", f"{len(comparison['confidence_changes'])} confidence-state change(s) were detected.", {"confidence_changes": comparison["confidence_changes"]})
        flags = snapshot["governance_state"]
        approval_valid = flags.get("approval_valid_until")
        reassessment = flags.get("reassessment_at")
        now_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if approval_valid and datetime.fromisoformat(approval_valid.replace("Z", "+00:00")) < now_dt:
            emit("approval_expired", "critical", "Approval expired", "The final governance approval has expired and publication should stop pending reassessment.")
        elif reassessment and datetime.fromisoformat(reassessment.replace("Z", "+00:00")) <= now_dt:
            emit("reassessment_due", "high", "Reassessment is due", "The governed narrative has reached its reassessment date.")
        next_check = self._next_watch_check(watch["cadence"], timestamp)
        with self._transaction() as connection:
            connection.execute("UPDATE watchlists SET last_checked_at=?,next_check_at=?,updated_at=? WHERE watch_id=?", (timestamp, next_check, timestamp, watch["watch_id"]))
            self._activity(connection, watch["case_id"], "watchlist_checked", entity_id=watch["watch_id"],
                           payload={"snapshot_id": snapshot["snapshot_id"], "comparison_id": comparison["comparison_id"] if comparison else None, "alert_count": len(generated_alerts)}, created_at=timestamp)
        return {"watchlist": self.get_watchlist(watch["watch_id"]), "snapshot": snapshot, "comparison": comparison, "alerts": generated_alerts, "alert_count": len(generated_alerts)}

    def ingest_site_intelligence_event(self, payload: Mapping[str, Any], *, ingested_at: str | None = None) -> Dict[str, Any]:
        handoff = validate_site_intelligence_handoff(payload)
        self.get_case(handoff["case_id"])
        timestamp = monitoring_datetime(ingested_at, "ingested_at") if ingested_at else _iso_now()
        digest = sha256_digest(handoff)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO site_intelligence_events(event_id,case_id,event_type,observed_at,handoff_json,handoff_sha256,ingested_at) VALUES(?,?,?,?,?,?,?)",
                    (handoff["event_id"], handoff["case_id"], handoff["event_type"], handoff["observed_at"], _json_dump(handoff), digest, timestamp),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"Site Intelligence event already exists: {handoff['event_id']}") from exc
            self._activity(connection, handoff["case_id"], "site_intelligence_event_ingested", entity_id=handoff["event_id"],
                           payload={"event_type": handoff["event_type"], "confidence": handoff["confidence"], "handoff_sha256": digest}, created_at=timestamp)
        alerts = []
        for watch in self.list_watchlists(case_id=handoff["case_id"], status="active"):
            if "site_intelligence_event" in watch["trigger_types"]:
                alerts.append(self.create_monitoring_alert(
                    case_id=handoff["case_id"], watch_id=watch["watch_id"], alert_type="site_intelligence_event",
                    severity="high" if handoff["confidence"] == "high" and handoff["event_type"] == "material_change" else "medium",
                    title=handoff["headline"], body=handoff["summary"] or "Site Intelligence reported a monitored event.",
                    metadata={"event_id": handoff["event_id"], "event_type": handoff["event_type"], "source_url": handoff["source_url"]}, created_at=timestamp,
                ))
        return {"handoff": handoff, "handoff_sha256": digest, "ingested_at": timestamp, "alerts": alerts}

    def list_site_intelligence_events(self, case_id: str) -> List[Dict[str, Any]]:
        normalized_case = _urn_uuid(case_id, "case_id")
        with self._lock:
            rows = self._connection.execute("SELECT handoff_json FROM site_intelligence_events WHERE case_id=? ORDER BY observed_at,event_id", (normalized_case,)).fetchall()
        return [_json_load(row["handoff_json"]) for row in rows]

    def case_timeline(self, case_id: str) -> Dict[str, Any]:
        case = self.get_case(case_id)
        events: List[Dict[str, Any]] = []
        for revision in self.list_revisions(case["case_id"]):
            events.append({"occurred_at": revision["created_at"], "event_type": "revision", "entity_id": revision["revision_id"], "summary": revision["change_note"], "payload": {"revision_number": revision["revision_number"], "risk_score": revision["record"]["calculations"]["risk_score"]}})
        for review in self.list_review_events(case["case_id"]):
            events.append({"occurred_at": review["created_at"], "event_type": "review_event", "entity_id": review["event_id"], "summary": review["body"], "payload": {"review_event_type": review["event_type"]}})
        for decision in self.list_governance_decisions(case_id=case["case_id"]):
            events.append({"occurred_at": decision["decided_at"], "event_type": "governance_decision", "entity_id": decision["decision_id"], "summary": decision["rationale"], "payload": {"stage": decision["stage"], "disposition": decision["disposition"]}})
        for snapshot in self.list_monitoring_snapshots(case["case_id"]):
            events.append({"occurred_at": snapshot["captured_at"], "event_type": "monitoring_snapshot", "entity_id": snapshot["snapshot_id"], "summary": f"Captured {snapshot['trigger']} snapshot.", "payload": {"risk_score": snapshot["risk_score"], "freshness": snapshot["freshness_report"]["status"]}})
        for comparison in self.list_monitoring_comparisons(case["case_id"]):
            events.append({"occurred_at": comparison["compared_at"], "event_type": "monitoring_comparison", "entity_id": comparison["comparison_id"], "summary": " ".join(comparison["reasons"]), "payload": {"materiality_score": comparison["materiality_score"], "severity": comparison["severity"]}})
        for alert in self.list_monitoring_alerts(case_id=case["case_id"]):
            events.append({"occurred_at": alert["created_at"], "event_type": "monitoring_alert", "entity_id": alert["alert_id"], "summary": alert["title"], "payload": {"alert_type": alert["alert_type"], "severity": alert["severity"], "status": alert["status"]}})
        for handoff in self.list_site_intelligence_events(case["case_id"]):
            events.append({"occurred_at": handoff["observed_at"], "event_type": "site_intelligence_event", "entity_id": handoff["event_id"], "summary": handoff["headline"], "payload": {"event_type": handoff["event_type"], "confidence": handoff["confidence"]}})
        events.sort(key=lambda item: (item["occurred_at"], item["event_type"], item["entity_id"]))
        return {"case_id": case["case_id"], "timeline_version": VERSION, "events": events, "count": len(events)}

    # ------------------------------------------------------------------
    # v2.0.0 governed review workflow

    def _template_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        template = {
            "template_id": row["template_id"], "name": row["name"], "description": row["description"],
            "stages": _json_load(row["stages_json"]), "default_due_days": int(row["default_due_days"]),
            "escalation_days": int(row["escalation_days"]), "created_at": row["created_at"],
            "updated_at": row["updated_at"], "created_by": row["created_by"], "active": bool(row["active"]),
        }
        _schema_error("review template", template, REVIEW_TEMPLATE_SCHEMA_PATH)
        return template

    def create_review_template(
        self, *, name: str | None = None, description: str | None = None,
        stages: Sequence[Mapping[str, Any]] | None = None, default_due_days: int | None = None,
        escalation_days: int | None = None, active: bool = True, template_id: str | None = None,
        created_at: str | None = None, created_by: str | None = None, actor_role: str = "administrator",
    ) -> Dict[str, Any]:
        require_permission(actor_role, "manage_templates")
        defaults = default_template_payload()
        normalized_id = _urn_uuid(template_id, "template_id")
        timestamp = _validate_datetime(created_at, "created_at") if created_at else _iso_now()
        normalized_name = _text(name if name is not None else defaults["name"], "name", required=True, maximum=500)
        normalized_description = _text(description if description is not None else defaults["description"], "description", maximum=20000)
        normalized_stages = normalize_template_stages(stages if stages is not None else defaults["stages"])
        due_days = defaults["default_due_days"] if default_due_days is None else default_due_days
        escalation = defaults["escalation_days"] if escalation_days is None else escalation_days
        if not isinstance(due_days, int) or isinstance(due_days, bool) or not 0 <= due_days <= 3650:
            raise NarrativeRiskValidationError("default_due_days must be an integer between 0 and 3650")
        if not isinstance(escalation, int) or isinstance(escalation, bool) or not 0 <= escalation <= 3650:
            raise NarrativeRiskValidationError("escalation_days must be an integer between 0 and 3650")
        if not isinstance(active, bool):
            raise NarrativeRiskValidationError("active must be a boolean")
        template = {
            "template_id": normalized_id, "name": normalized_name, "description": normalized_description,
            "stages": normalized_stages, "default_due_days": due_days, "escalation_days": escalation,
            "created_at": timestamp, "updated_at": timestamp,
            "created_by": _nullable_text(created_by, "created_by"), "active": active,
        }
        _schema_error("review template", template, REVIEW_TEMPLATE_SCHEMA_PATH)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO review_templates(template_id,name,description,stages_json,default_due_days,escalation_days,created_at,updated_at,created_by,active) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (normalized_id, normalized_name, normalized_description, _json_dump(normalized_stages), due_days, escalation,
                     timestamp, timestamp, template["created_by"], int(active)),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"review template already exists: {normalized_id}") from exc
        return template

    def get_review_template(self, template_id: str) -> Dict[str, Any]:
        normalized_id = _urn_uuid(template_id, "template_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM review_templates WHERE template_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"review template not found: {normalized_id}")
        return self._template_from_row(row)

    def list_review_templates(self, *, active: bool | None = None) -> List[Dict[str, Any]]:
        if active is not None and not isinstance(active, bool):
            raise NarrativeRiskValidationError("active must be a boolean or null")
        with self._lock:
            if active is None:
                rows = self._connection.execute("SELECT * FROM review_templates ORDER BY name, template_id").fetchall()
            else:
                rows = self._connection.execute("SELECT * FROM review_templates WHERE active=? ORDER BY name, template_id", (int(active),)).fetchall()
        return [self._template_from_row(row) for row in rows]

    def _assignment_from_row(self, row: sqlite3.Row, *, at: str | None = None) -> Dict[str, Any]:
        status = row["status"]
        if status in {"pending", "accepted"} and row["due_at"] and is_past(row["due_at"], at=at):
            status = "overdue"
        assignment = {
            "assignment_id": row["assignment_id"], "case_id": row["case_id"], "revision_id": row["revision_id"],
            "workflow_id": row["workflow_id"], "stage": row["stage"], "reviewer_id": row["reviewer_id"],
            "reviewer_name": row["reviewer_name"], "reviewer_role": row["reviewer_role"], "status": status,
            "required": bool(row["required"]), "instructions": row["instructions"], "created_at": row["created_at"],
            "created_by": row["created_by"], "due_at": row["due_at"], "accepted_at": row["accepted_at"],
            "completed_at": row["completed_at"], "escalated_at": row["escalated_at"],
        }
        _schema_error("review assignment", assignment, REVIEW_ASSIGNMENT_SCHEMA_PATH)
        return assignment

    def _decision_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        decision = {
            "decision_id": row["decision_id"], "case_id": row["case_id"], "revision_id": row["revision_id"],
            "workflow_id": row["workflow_id"], "assignment_id": row["assignment_id"], "stage": row["stage"],
            "disposition": row["disposition"], "decided_by": row["decided_by"], "decided_by_name": row["decided_by_name"],
            "decider_role": row["decider_role"], "decided_at": row["decided_at"], "rationale": row["rationale"],
            "conditions": _json_load(row["conditions_json"]), "required_wording": _json_load(row["required_wording_json"]),
            "publication_restrictions": _json_load(row["publication_restrictions_json"]),
            "disclosures": _json_load(row["disclosures_json"]), "valid_until": row["valid_until"],
            "reassessment_at": row["reassessment_at"], "supersedes_decision_id": row["supersedes_decision_id"],
        }
        _schema_error("governance decision", decision, GOVERNANCE_DECISION_SCHEMA_PATH)
        return decision

    def _workflow_from_row(self, row: sqlite3.Row, *, at: str | None = None) -> Dict[str, Any]:
        workflow_id = row["workflow_id"]
        assignments = self.list_review_assignments(workflow_id=workflow_id, at=at)
        decisions = self.list_governance_decisions(workflow_id=workflow_id)
        required_complete = all(item["status"] in {"completed", "waived"} for item in assignments if item["required"])
        final = next((item for item in reversed(decisions) if item["stage"] == "final"), None)
        status = row["status"]
        flags: List[str] = []
        approval_valid_until = final["valid_until"] if final and final["disposition"] in {"approve", "approve_with_conditions"} else None
        reassessment_at = final["reassessment_at"] if final else None
        if status == "approved" and approval_valid_until and is_past(approval_valid_until, at=at):
            status = "expired"
            flags.append("approval_expired")
        if reassessment_at and is_past(reassessment_at, at=at):
            flags.append("reassessment_due")
        if any(item["status"] == "overdue" and item["required"] for item in assignments):
            flags.append("required_review_overdue")
        blocking = {"internal_only", "embargoed", "no_public_claim", "legal_review_required"}
        publication_allowed = bool(
            status == "approved" and final and final["disposition"] in {"approve", "approve_with_conditions"}
            and not (set(final["publication_restrictions"]) & blocking) and "reassessment_due" not in flags
        )
        workflow = {
            "workflow_id": workflow_id, "case_id": row["case_id"], "revision_id": row["revision_id"],
            "template_id": row["template_id"], "template_snapshot": _json_load(row["template_snapshot_json"]),
            "status": status, "current_stage": row["current_stage"], "started_at": row["started_at"],
            "due_at": row["due_at"], "completed_at": row["completed_at"], "created_by": row["created_by"],
            "updated_at": row["updated_at"], "assignment_count": len(assignments), "decision_count": len(decisions),
            "required_assignments_complete": required_complete,
            "final_disposition": final["disposition"] if final else None,
            "approval_valid_until": approval_valid_until, "reassessment_at": reassessment_at,
            "publication_allowed": publication_allowed, "governance_flags": flags,
        }
        _schema_error("governance workflow", workflow, GOVERNANCE_WORKFLOW_SCHEMA_PATH)
        return workflow

    def start_governance_workflow(
        self, case_id: str, *, revision_id: str | None = None, template_id: str | None = None,
        template_snapshot: Mapping[str, Any] | None = None, workflow_id: str | None = None,
        started_at: str | None = None, due_at: str | None = None, created_by: str | None = None,
        actor_role: str = "administrator",
    ) -> Dict[str, Any]:
        require_permission(actor_role, "assign_reviewers")
        case = self.get_case(case_id)
        revisions = self.list_revisions(case["case_id"])
        if not revisions:
            raise NarrativeRiskValidationError("a governance workflow requires at least one immutable revision")
        revision = self.get_revision(revision_id) if revision_id else revisions[-1]
        if revision["case_id"] != case["case_id"]:
            raise NarrativeRiskValidationError("workflow revision does not belong to the case")
        normalized_workflow_id = _urn_uuid(workflow_id, "workflow_id")
        timestamp = _validate_datetime(started_at, "started_at") if started_at else _iso_now()
        normalized_due = _validate_datetime(due_at, "due_at") if due_at else None
        normalized_template_id = None
        if template_snapshot is not None and template_id is not None:
            raise NarrativeRiskValidationError("provide template_id or template_snapshot, not both")
        if template_id is not None:
            template = self.get_review_template(template_id)
            normalized_template_id = template["template_id"]
        elif template_snapshot is not None:
            if not isinstance(template_snapshot, Mapping):
                raise NarrativeRiskValidationError("template_snapshot must be a JSON object")
            raw = dict(template_snapshot)
            template = {
                "name": _text(raw.get("name", "Case review"), "template_snapshot.name", required=True, maximum=500),
                "description": _text(raw.get("description", ""), "template_snapshot.description", maximum=20000),
                "stages": normalize_template_stages(raw.get("stages")),
                "default_due_days": int(raw.get("default_due_days", 14)),
                "escalation_days": int(raw.get("escalation_days", 3)),
            }
        else:
            template = default_template_payload()
            template = {key: template[key] for key in ("name", "description", "stages", "default_due_days", "escalation_days")}
        stages = normalize_template_stages(template["stages"])
        template["stages"] = stages
        first_stage = stages[0]["stage"]
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO governance_workflows(workflow_id,case_id,revision_id,template_id,template_snapshot_json,status,current_stage,started_at,due_at,completed_at,created_by,updated_at) VALUES(?,?,?,?,?,'active',?,?,?,NULL,?,?)",
                    (normalized_workflow_id, case["case_id"], revision["revision_id"], normalized_template_id,
                     _json_dump(template), first_stage, timestamp, normalized_due, _nullable_text(created_by, "created_by"), timestamp),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"case already has a governance workflow: {case['case_id']}") from exc
            connection.execute("UPDATE cases SET status='in_review', updated_at=? WHERE case_id=?", (timestamp, case["case_id"]))
            self._activity(connection, case["case_id"], "governance_workflow_started", entity_id=normalized_workflow_id,
                           payload={"revision_id": revision["revision_id"], "current_stage": first_stage}, created_at=timestamp)
        return self.get_governance_workflow(normalized_workflow_id)

    def get_governance_workflow(self, workflow_id: str, *, include_details: bool = False, at: str | None = None) -> Dict[str, Any]:
        normalized_id = _urn_uuid(workflow_id, "workflow_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM governance_workflows WHERE workflow_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"governance workflow not found: {normalized_id}")
        workflow = self._workflow_from_row(row, at=at)
        if include_details:
            workflow["review_assignments"] = self.list_review_assignments(workflow_id=normalized_id, at=at)
            workflow["governance_decisions"] = self.list_governance_decisions(workflow_id=normalized_id)
        return workflow

    def get_case_governance_workflow(self, case_id: str, *, include_details: bool = False, at: str | None = None) -> Dict[str, Any] | None:
        normalized_case = _urn_uuid(case_id, "case_id")
        with self._lock:
            row = self._connection.execute("SELECT workflow_id FROM governance_workflows WHERE case_id=?", (normalized_case,)).fetchone()
        return None if row is None else self.get_governance_workflow(row["workflow_id"], include_details=include_details, at=at)

    def assign_reviewer(
        self, workflow_id: str, *, stage: str, reviewer_id: str, reviewer_role: str,
        reviewer_name: str | None = None, required: bool = True, instructions: str = "",
        due_at: str | None = None, assignment_id: str | None = None, created_at: str | None = None,
        created_by: str | None = None, actor_role: str = "administrator",
    ) -> Dict[str, Any]:
        require_permission(actor_role, "assign_reviewers")
        workflow = self.get_governance_workflow(workflow_id)
        normalized_stage = _choice(stage, "stage", REVIEW_STAGES, "intake")
        template_stage = next((item for item in workflow["template_snapshot"]["stages"] if item["stage"] == normalized_stage), None)
        if template_stage is None:
            raise NarrativeRiskValidationError(f"stage is not included in this workflow template: {normalized_stage}")
        normalized_role = _choice(reviewer_role, "reviewer_role", REVIEWER_ROLES, template_stage["required_role"])
        if normalized_role != template_stage["required_role"] and actor_role != "administrator":
            raise NarrativeRiskValidationError(f"stage {normalized_stage} requires role {template_stage['required_role']}")
        if not isinstance(required, bool):
            raise NarrativeRiskValidationError("required must be a boolean")
        normalized_id = _urn_uuid(assignment_id, "assignment_id")
        timestamp = _validate_datetime(created_at, "created_at") if created_at else _iso_now()
        normalized_due = _validate_datetime(due_at, "due_at") if due_at else None
        assignment = {
            "assignment_id": normalized_id, "case_id": workflow["case_id"], "revision_id": workflow["revision_id"],
            "workflow_id": workflow["workflow_id"], "stage": normalized_stage,
            "reviewer_id": _text(reviewer_id, "reviewer_id", required=True, maximum=500),
            "reviewer_name": _nullable_text(reviewer_name, "reviewer_name"), "reviewer_role": normalized_role,
            "status": "pending", "required": required, "instructions": _text(instructions or template_stage["instructions"], "instructions", maximum=20000),
            "created_at": timestamp, "created_by": _nullable_text(created_by, "created_by"), "due_at": normalized_due,
            "accepted_at": None, "completed_at": None, "escalated_at": None,
        }
        _schema_error("review assignment", assignment, REVIEW_ASSIGNMENT_SCHEMA_PATH)
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO review_assignments(assignment_id,case_id,revision_id,workflow_id,stage,reviewer_id,reviewer_name,reviewer_role,status,required,instructions,created_at,created_by,due_at,accepted_at,completed_at,escalated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (assignment["assignment_id"], assignment["case_id"], assignment["revision_id"], assignment["workflow_id"], assignment["stage"],
                     assignment["reviewer_id"], assignment["reviewer_name"], assignment["reviewer_role"], assignment["status"], int(required),
                     assignment["instructions"], timestamp, assignment["created_by"], normalized_due, None, None, None),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"review assignment already exists: {normalized_id}") from exc
            self._activity(connection, assignment["case_id"], "reviewer_assigned", entity_id=normalized_id,
                           payload={"stage": normalized_stage, "reviewer_id": assignment["reviewer_id"], "required": required}, created_at=timestamp)
        return assignment

    def get_review_assignment(self, assignment_id: str, *, at: str | None = None) -> Dict[str, Any]:
        normalized_id = _urn_uuid(assignment_id, "assignment_id")
        with self._lock:
            row = self._connection.execute("SELECT * FROM review_assignments WHERE assignment_id=?", (normalized_id,)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError(f"review assignment not found: {normalized_id}")
        return self._assignment_from_row(row, at=at)

    def list_review_assignments(
        self, *, workflow_id: str | None = None, case_id: str | None = None, reviewer_id: str | None = None,
        status: str | None = None, stage: str | None = None, at: str | None = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if workflow_id is not None: clauses.append("workflow_id=?"); params.append(_urn_uuid(workflow_id, "workflow_id"))
        if case_id is not None: clauses.append("case_id=?"); params.append(_urn_uuid(case_id, "case_id"))
        if reviewer_id is not None: clauses.append("reviewer_id=?"); params.append(_text(reviewer_id, "reviewer_id", required=True, maximum=500))
        normalized_status = None if status is None else _choice(status, "status", ASSIGNMENT_STATUSES, "pending")
        if stage is not None: clauses.append("stage=?"); params.append(_choice(stage, "stage", REVIEW_STAGES, "intake"))
        sql = "SELECT * FROM review_assignments" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY due_at IS NULL, due_at, created_at, assignment_id"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        output = [self._assignment_from_row(row, at=at) for row in rows]
        return [item for item in output if normalized_status is None or item["status"] == normalized_status]

    def update_review_assignment_status(
        self, assignment_id: str, *, status: str, actor_id: str, actor_role: str,
        changed_at: str | None = None,
    ) -> Dict[str, Any]:
        assignment = self.get_review_assignment(assignment_id)
        normalized_status = _choice(status, "status", ASSIGNMENT_STATUSES, "pending")
        if normalized_status == "completed":
            require_permission(actor_role, "submit_review")
        elif normalized_status in {"waived", "overdue"}:
            require_permission(actor_role, "assign_reviewers")
        elif assignment["reviewer_id"] != actor_id and actor_role != "administrator":
            raise NarrativeRiskValidationError("only the assigned reviewer or an administrator may accept the assignment")
        timestamp = _validate_datetime(changed_at, "changed_at") if changed_at else _iso_now()
        accepted_at = timestamp if normalized_status == "accepted" else assignment["accepted_at"]
        completed_at = timestamp if normalized_status in {"completed", "waived"} else assignment["completed_at"]
        escalated_at = timestamp if normalized_status == "overdue" else assignment["escalated_at"]
        stored_status = normalized_status
        with self._transaction() as connection:
            connection.execute("UPDATE review_assignments SET status=?, accepted_at=?, completed_at=?, escalated_at=? WHERE assignment_id=?",
                               (stored_status, accepted_at, completed_at, escalated_at, assignment["assignment_id"]))
            self._activity(connection, assignment["case_id"], "assignment_status_changed", entity_id=assignment["assignment_id"],
                           payload={"status": stored_status, "actor_id": actor_id, "actor_role": actor_role}, created_at=timestamp)
        return self.get_review_assignment(assignment["assignment_id"], at=timestamp)

    def list_governance_decisions(
        self, *, workflow_id: str | None = None, case_id: str | None = None, stage: str | None = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if workflow_id is not None: clauses.append("workflow_id=?"); params.append(_urn_uuid(workflow_id, "workflow_id"))
        if case_id is not None: clauses.append("case_id=?"); params.append(_urn_uuid(case_id, "case_id"))
        if stage is not None: clauses.append("stage=?"); params.append(_choice(stage, "stage", REVIEW_STAGES, "intake"))
        sql = "SELECT * FROM governance_decisions" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY decided_at, decision_id"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        return [self._decision_from_row(row) for row in rows]

    def add_governance_decision(
        self, workflow_id: str, *, stage: str, disposition: str, decided_by: str, decider_role: str,
        rationale: str, assignment_id: str | None = None, decided_by_name: str | None = None,
        conditions: Sequence[str] | None = None, required_wording: Sequence[str] | None = None,
        publication_restrictions: Sequence[str] | None = None, disclosures: Sequence[str] | None = None,
        valid_until: str | None = None, reassessment_at: str | None = None,
        supersedes_decision_id: str | None = None, decision_id: str | None = None, decided_at: str | None = None,
    ) -> Dict[str, Any]:
        workflow = self.get_governance_workflow(workflow_id, include_details=True)
        normalized_stage = _choice(stage, "stage", REVIEW_STAGES, workflow["current_stage"])
        normalized_disposition = _choice(disposition, "disposition", GOVERNANCE_DISPOSITIONS, "revise")
        normalized_role = _choice(decider_role, "decider_role", REVIEWER_ROLES, "reviewer")
        require_permission(normalized_role, "decide_stage")
        if normalized_stage == "final" and normalized_disposition in {"approve", "approve_with_conditions"}:
            require_permission(normalized_role, "approve_final")
        if workflow["status"] in {"approved", "rejected", "expired", "closed"} and supersedes_decision_id is None:
            raise NarrativeRiskValidationError("completed governance workflow requires an explicit supersedes_decision_id")
        if normalized_stage != workflow["current_stage"] and normalized_role != "administrator":
            raise NarrativeRiskValidationError(f"workflow is currently at stage {workflow['current_stage']}")
        template_stage_definition = next(item for item in workflow["template_snapshot"]["stages"] if item["stage"] == normalized_stage)
        normalized_assignment_id = _urn_uuid(assignment_id, "assignment_id") if assignment_id else None
        if template_stage_definition["required"] and normalized_assignment_id is None:
            raise NarrativeRiskValidationError(f"required review stage {normalized_stage} requires a review assignment")
        assignment = None
        if normalized_assignment_id:
            assignment = self.get_review_assignment(normalized_assignment_id)
            if assignment["workflow_id"] != workflow["workflow_id"] or assignment["stage"] != normalized_stage:
                raise NarrativeRiskValidationError("assignment does not belong to this workflow stage")
            if assignment["reviewer_id"] != decided_by and normalized_role != "administrator":
                raise NarrativeRiskValidationError("decision actor does not match the assigned reviewer")
        normalized_conditions = normalize_string_list(conditions, "conditions", maximum=100, item_maximum=2000)
        normalized_wording = normalize_string_list(required_wording, "required_wording", maximum=100, item_maximum=5000)
        normalized_restrictions = normalize_string_list(publication_restrictions, "publication_restrictions", allowed=PUBLICATION_RESTRICTIONS)
        normalized_disclosures = normalize_string_list(disclosures, "disclosures", maximum=100, item_maximum=5000)
        if normalized_disposition == "approve_with_conditions" and not (normalized_conditions or normalized_wording or normalized_restrictions or normalized_disclosures):
            raise NarrativeRiskValidationError("approve_with_conditions requires at least one condition, required wording, restriction, or disclosure")
        normalized_valid_until = _validate_datetime(valid_until, "valid_until") if valid_until else None
        normalized_reassessment = _validate_datetime(reassessment_at, "reassessment_at") if reassessment_at else None
        timestamp = _validate_datetime(decided_at, "decided_at") if decided_at else _iso_now()
        if normalized_valid_until and is_past(normalized_valid_until, at=timestamp):
            raise NarrativeRiskValidationError("valid_until must be later than decided_at")
        if normalized_reassessment and normalized_valid_until:
            if datetime.fromisoformat(normalized_reassessment.replace("Z", "+00:00")) > datetime.fromisoformat(normalized_valid_until.replace("Z", "+00:00")):
                raise NarrativeRiskValidationError("reassessment_at must not be later than valid_until")
        normalized_supersedes = _urn_uuid(supersedes_decision_id, "supersedes_decision_id") if supersedes_decision_id else None
        if normalized_supersedes:
            prior = next((item for item in workflow["governance_decisions"] if item["decision_id"] == normalized_supersedes), None)
            if prior is None:
                raise NarrativeRiskValidationError("supersedes_decision_id does not belong to this workflow")
        normalized_id = _urn_uuid(decision_id, "decision_id")
        decision = {
            "decision_id": normalized_id, "case_id": workflow["case_id"], "revision_id": workflow["revision_id"],
            "workflow_id": workflow["workflow_id"], "assignment_id": normalized_assignment_id, "stage": normalized_stage,
            "disposition": normalized_disposition, "decided_by": _text(decided_by, "decided_by", required=True, maximum=500),
            "decided_by_name": _nullable_text(decided_by_name, "decided_by_name"), "decider_role": normalized_role,
            "decided_at": timestamp, "rationale": _text(rationale, "rationale", required=True, maximum=50000),
            "conditions": normalized_conditions, "required_wording": normalized_wording,
            "publication_restrictions": normalized_restrictions, "disclosures": normalized_disclosures,
            "valid_until": normalized_valid_until, "reassessment_at": normalized_reassessment,
            "supersedes_decision_id": normalized_supersedes,
        }
        _schema_error("governance decision", decision, GOVERNANCE_DECISION_SCHEMA_PATH)

        template_stages = workflow["template_snapshot"]["stages"]
        current_index = next(i for i, item in enumerate(template_stages) if item["stage"] == normalized_stage)
        next_stage = template_stages[current_index + 1]["stage"] if current_index + 1 < len(template_stages) else "final"
        workflow_status = "active"
        completed_at = None
        case_status = "in_review"
        if normalized_disposition == "revise":
            workflow_status = "changes_required"
        elif normalized_disposition == "reject":
            workflow_status = "rejected"; completed_at = timestamp; case_status = "closed"
        elif normalized_stage == "final" and normalized_disposition in {"approve", "approve_with_conditions"}:
            required_stages = {item["stage"] for item in template_stages if item["required"]}
            required_assignments = workflow["review_assignments"]
            complete_stages = {
                item["stage"] for item in required_assignments
                if item["required"] and (item["status"] in {"completed", "waived"} or item["assignment_id"] == normalized_assignment_id)
            }
            missing_stages = sorted(required_stages - complete_stages, key=REVIEW_STAGES.index)
            if missing_stages:
                raise NarrativeRiskValidationError(
                    "final approval requires a completed or waived assignment for required stage(s): " + ", ".join(missing_stages)
                )
            blocking = [item for item in workflow["governance_decisions"] if item["disposition"] in {"revise", "reject"} and not any(d.get("supersedes_decision_id") == item["decision_id"] for d in workflow["governance_decisions"])]
            if blocking:
                raise NarrativeRiskValidationError("final approval cannot proceed while an unsuperseded revise or reject decision remains")
            workflow_status = "approved"; completed_at = timestamp; case_status = "approved"; next_stage = "final"
        elif normalized_disposition in {"approve", "approve_with_conditions", "waive"}:
            next_stage = template_stages[current_index + 1]["stage"] if current_index + 1 < len(template_stages) else "final"

        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO governance_decisions(decision_id,case_id,revision_id,workflow_id,assignment_id,stage,disposition,decided_by,decided_by_name,decider_role,decided_at,rationale,conditions_json,required_wording_json,publication_restrictions_json,disclosures_json,valid_until,reassessment_at,supersedes_decision_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (normalized_id, decision["case_id"], decision["revision_id"], decision["workflow_id"], normalized_assignment_id,
                     normalized_stage, normalized_disposition, decision["decided_by"], decision["decided_by_name"], normalized_role,
                     timestamp, decision["rationale"], _json_dump(normalized_conditions), _json_dump(normalized_wording),
                     _json_dump(normalized_restrictions), _json_dump(normalized_disclosures), normalized_valid_until,
                     normalized_reassessment, normalized_supersedes),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"governance decision already exists: {normalized_id}") from exc
            if normalized_assignment_id:
                connection.execute("UPDATE review_assignments SET status='completed', completed_at=? WHERE assignment_id=?", (timestamp, normalized_assignment_id))
            connection.execute("UPDATE governance_workflows SET status=?, current_stage=?, completed_at=?, updated_at=? WHERE workflow_id=?",
                               (workflow_status, next_stage, completed_at, timestamp, workflow["workflow_id"]))
            connection.execute("UPDATE cases SET status=?, updated_at=? WHERE case_id=?", (case_status, timestamp, workflow["case_id"]))
            self._activity(connection, workflow["case_id"], "governance_decision_added", entity_id=normalized_id,
                           payload={"stage": normalized_stage, "disposition": normalized_disposition, "workflow_status": workflow_status}, created_at=timestamp)
        return self._decision_from_row(self._connection.execute("SELECT * FROM governance_decisions WHERE decision_id=?", (normalized_id,)).fetchone())

    def governance_queue(self, *, reviewer_id: str | None = None, at: str | None = None) -> Dict[str, Any]:
        assignments = self.list_review_assignments(reviewer_id=reviewer_id, at=at)
        queues = {status: [item for item in assignments if item["status"] == status] for status in sorted(ASSIGNMENT_STATUSES)}
        due = self.list_reassessment_due(at=at)
        return {"assignments": assignments, "queues": queues, "reassessment_due": due, "count": len(assignments)}

    def list_reassessment_due(self, *, at: str | None = None) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute("SELECT workflow_id FROM governance_workflows WHERE status IN ('approved','active','changes_required') ORDER BY updated_at").fetchall()
        output = []
        for row in rows:
            workflow = self.get_governance_workflow(row["workflow_id"], at=at)
            if "approval_expired" in workflow["governance_flags"] or "reassessment_due" in workflow["governance_flags"]:
                output.append(workflow)
        return output


    # ------------------------------------------------------------------
    # v2.0.0 security, privacy, backup, and production hardening

    def database_diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            integrity = str(self._connection.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_key_rows = self._connection.execute("PRAGMA foreign_key_check").fetchall()
            journal_mode = str(self._connection.execute("PRAGMA journal_mode").fetchone()[0])
            page_count = int(self._connection.execute("PRAGMA page_count").fetchone()[0])
            page_size = int(self._connection.execute("PRAGMA page_size").fetchone()[0])
            index_count = int(self._connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'").fetchone()[0])
            table_count = int(self._connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0])
        file_size = 0
        if self.database_path != ":memory:" and Path(self.database_path).exists():
            file_size = Path(self.database_path).stat().st_size
        return {
            "workspace_version": VERSION, "database_path": self.database_path,
            "integrity_check": integrity, "foreign_key_violation_count": len(foreign_key_rows),
            "journal_mode": journal_mode, "page_count": page_count, "page_size": page_size,
            "estimated_database_bytes": page_count * page_size, "database_file_bytes": file_size,
            "table_count": table_count, "index_count": index_count,
        }

    def save_privacy_policy(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        policy = normalize_privacy_policy(payload)
        with self._transaction() as connection:
            if policy["status"] == "active" and connection.execute("SELECT 1 FROM privacy_policies WHERE status='active' LIMIT 1").fetchone():
                raise NarrativeRiskValidationError("an active privacy policy already exists; retire it explicitly before activating another")
            try:
                connection.execute(
                    "INSERT INTO privacy_policies(policy_id,policy_json,policy_sha256,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (policy["policy_id"], _json_dump(policy), policy["policy_sha256"], policy["status"], policy["created_at"], policy["updated_at"]),
                )
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"privacy policy already exists: {policy['policy_id']}") from exc
        return policy

    def list_privacy_policies(self, *, status: str | None = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        sql = "SELECT policy_json FROM privacy_policies"
        if status is not None:
            normalized = _choice(status, "status", {"draft", "active", "retired"}, "draft")
            sql += " WHERE status=?"; params.append(normalized)
        sql += " ORDER BY updated_at DESC, policy_id"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        values = [_json_load(row["policy_json"]) for row in rows]
        for value in values:
            _schema_error("privacy policy", value, PRIVACY_POLICY_SCHEMA_PATH)
            if sha256_digest({k:v for k,v in value.items() if k!="policy_sha256"}) != value["policy_sha256"]:
                raise NarrativeRiskValidationError("privacy policy hash mismatch")
        return values

    def get_privacy_policy(self, policy_id: str | None = None) -> Dict[str, Any]:
        with self._lock:
            if policy_id is None:
                row = self._connection.execute("SELECT policy_json FROM privacy_policies WHERE status='active' ORDER BY updated_at DESC LIMIT 1").fetchone()
            else:
                row = self._connection.execute("SELECT policy_json FROM privacy_policies WHERE policy_id=?", (_urn_uuid(policy_id,"policy_id"),)).fetchone()
        if row is None:
            raise NarrativeRiskValidationError("privacy policy not found")
        value = _json_load(row["policy_json"]); _schema_error("privacy policy",value,PRIVACY_POLICY_SCHEMA_PATH)
        return value

    def _retention_case_detail(self, case_id: str) -> Dict[str, Any]:
        case = self.get_case(case_id)
        case.update({
            "revisions": self.list_revisions(case_id), "review_events": self.list_review_events(case_id),
            "governance_workflow": self.get_case_governance_workflow(case_id),
            "review_assignments": self.list_review_assignments(case_id=case_id),
            "governance_decisions": self.list_governance_decisions(case_id=case_id),
            "monitoring_snapshots": self.list_monitoring_snapshots(case_id),
            "monitoring_comparisons": self.list_monitoring_comparisons(case_id),
            "watchlists": self.list_watchlists(case_id=case_id),
            "monitoring_alerts": self.list_monitoring_alerts(case_id=case_id),
            "site_intelligence_events": self.list_site_intelligence_events(case_id),
            "stakeholder_actors": self.list_stakeholder_actors(case_id),
            "stakeholder_relationships": self.list_stakeholder_relationships(case_id),
            "stakeholder_incentives": self.list_stakeholder_incentives(case_id),
            "stakeholder_pressures": self.list_stakeholder_pressures(case_id),
            "stakeholder_consequences": self.list_stakeholder_consequences(case_id),
            "comparison_sets": self.list_comparison_sets(case_id=case_id),
            "comparative_evidence_matrices": [m for c in self.list_comparison_sets(case_id=case_id) for m in self.list_comparative_evidence_matrices(c["comparison_id"])],
            "scenarios": self.list_scenarios(case_id=case_id), "scenario_results": self.list_scenario_results(case_id=case_id),
            "sensitivity_analyses": [a for c in self.list_comparison_sets(case_id=case_id) for a in self.list_sensitivity_analyses(c["comparison_id"])],
            "decision_studio_handoffs": self.list_decision_studio_handoffs(case_id),
            "publication_briefings": self.list_publication_briefings(case_id),
            "publication_packages": self.list_publication_packages(case_id),
            "public_embeds": self.list_public_embeds(case_id), "platform_handoffs": self.list_platform_handoffs(case_id),
            "activity": self.list_activity(case_id),
        })
        return case

    def assess_case_retention(self, case_id: str, *, policy_id: str | None = None, assessed_at: str | None = None, assessed_by: str | None = None, assessment_id: str | None = None) -> Dict[str, Any]:
        case = self.get_case(case_id)
        policy = self.get_privacy_policy(policy_id)
        assessment = build_retention_assessment(self._retention_case_detail(case["case_id"]), policy, assessed_at=assessed_at, assessed_by=assessed_by, assessment_id=assessment_id)
        with self._transaction() as connection:
            try:
                connection.execute("INSERT INTO retention_assessments(assessment_id,case_id,policy_id,assessment_json,assessment_sha256,status,assessed_at) VALUES(?,?,?,?,?,?,?)", (assessment["assessment_id"],assessment["case_id"],assessment["policy_id"],_json_dump(assessment),assessment["assessment_sha256"],assessment["status"],assessment["assessed_at"]))
            except sqlite3.IntegrityError as exc:
                raise NarrativeRiskValidationError(f"retention assessment already exists: {assessment['assessment_id']}") from exc
            self._activity(connection,case["case_id"],"retention_assessed",entity_id=assessment["assessment_id"],payload={"status":assessment["status"],"due_categories":assessment["due_categories"]},created_at=assessment["assessed_at"])
        return assessment

    def list_retention_assessments(self, case_id: str) -> List[Dict[str, Any]]:
        normalized = _urn_uuid(case_id,"case_id")
        with self._lock:
            rows=self._connection.execute("SELECT assessment_json FROM retention_assessments WHERE case_id=? ORDER BY assessed_at,assessment_id",(normalized,)).fetchall()
        values=[_json_load(row["assessment_json"]) for row in rows]
        for value in values:
            _schema_error("retention assessment",value,RETENTION_ASSESSMENT_SCHEMA_PATH)
        return values

    def create_database_backup(self, destination_path: str | Path, *, created_at: str | None = None, created_by: str | None = None, backup_id: str | None = None) -> Dict[str, Any]:
        manifest=create_sqlite_backup(self.database_path,destination_path,created_at=created_at,created_by=created_by,backup_id=backup_id)
        with self._transaction() as connection:
            connection.execute("INSERT INTO backup_manifests(backup_id,manifest_json,manifest_sha256,backup_path,created_at) VALUES(?,?,?,?,?)",(manifest["backup_id"],_json_dump(manifest),manifest["manifest_sha256"],manifest["backup_path"],manifest["created_at"]))
        return manifest

    def list_backup_manifests(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows=self._connection.execute("SELECT manifest_json FROM backup_manifests ORDER BY created_at DESC,backup_id").fetchall()
        values=[_json_load(row["manifest_json"]) for row in rows]
        for value in values: _schema_error("backup manifest",value,BACKUP_MANIFEST_SCHEMA_PATH)
        return values

    def verify_database_backup(self, backup_id: str, *, verified_at: str | None = None) -> Dict[str, Any]:
        normalized=_urn_uuid(backup_id,"backup_id")
        with self._lock:
            row=self._connection.execute("SELECT manifest_json FROM backup_manifests WHERE backup_id=?",(normalized,)).fetchone()
        if row is None: raise NarrativeRiskValidationError(f"backup manifest not found: {normalized}")
        return verify_sqlite_backup(_json_load(row["manifest_json"]),verified_at=verified_at)

    def restore_database_backup(self, backup_id: str, target_path: str | Path, *, overwrite: bool = False) -> Dict[str, Any]:
        normalized=_urn_uuid(backup_id,"backup_id")
        with self._lock:
            row=self._connection.execute("SELECT manifest_json FROM backup_manifests WHERE backup_id=?",(normalized,)).fetchone()
        if row is None: raise NarrativeRiskValidationError(f"backup manifest not found: {normalized}")
        return restore_sqlite_backup(_json_load(row["manifest_json"]),target_path,overwrite=overwrite)

    def performance_report(self, *, case_id: str | None = None, generated_at: str | None = None, report_id: str | None = None) -> Dict[str, Any]:
        return build_performance_report(self,case_id=case_id,generated_at=generated_at,report_id=report_id)
