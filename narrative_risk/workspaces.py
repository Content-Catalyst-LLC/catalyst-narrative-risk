"""SQLite-backed persistent cases, revisions, review events, and portable bundles.

The workspace layer treats canonical narrative-risk records as immutable revision
artifacts. Case metadata may change, while revisions and activity entries are
append-only. This module uses only Python's standard-library sqlite3 driver so
local and institutional deployments share the same repository contract.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
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
    canonical_json,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError
from .service import build_narrative_risk_record, validate_narrative_risk_record

VERSION = "1.4.0"
BUNDLE_TYPE = "catalyst_narrative_risk_case_bundle"
CASE_STATUSES = {"draft", "active", "in_review", "approved", "closed"}
CASE_PRIORITIES = {"low", "normal", "high", "critical"}
REVIEW_EVENT_TYPES = {
    "comment", "review_requested", "review_completed", "decision_updated",
    "status_changed", "assignment_changed",
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
            for table in ("cases", "revisions", "review_events", "saved_views", "activity"):
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
            "review_events": self.list_review_events(case["case_id"]), "activity": self.list_activity(case["case_id"]),
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
        }

    def import_case_bundle(self, bundle: Mapping[str, Any]) -> Dict[str, Any]:
        report = self.verify_bundle(bundle)
        if not report["bundle_sha256_match"]:
            raise NarrativeRiskValidationError("workspace bundle_sha256 does not match the bundle payload")
        if not report["all_revision_hashes_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a revision record hash mismatch")
        if not report["all_case_ids_match"]:
            raise NarrativeRiskValidationError("workspace bundle contains a revision for another case")
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
            for activity in bundle["activity"]:
                self._activity(
                    connection, activity["case_id"], activity["event_type"], entity_id=activity["entity_id"],
                    payload=activity["payload"], created_at=activity["created_at"], activity_id=activity["activity_id"],
                )
        imported = self.get_case(case_id, include_details=True)
        return {"case": imported, "verification": report}
