"""Security, privacy, backup, accessibility, and production-readiness controls for v2.0.0.

The hardening layer evaluates deployment controls and creates auditable reports. It
never certifies a deployment as secure by itself; operators remain responsible for
hosting, encryption, identity, network, and incident-response controls.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID, uuid4

from .contracts import (
    ACCESSIBILITY_REPORT_SCHEMA_PATH,
    BACKUP_MANIFEST_SCHEMA_PATH,
    PERFORMANCE_REPORT_SCHEMA_PATH,
    PRIVACY_POLICY_SCHEMA_PATH,
    PRODUCTION_READINESS_SCHEMA_PATH,
    RETENTION_ASSESSMENT_SCHEMA_PATH,
    SECURITY_REPORT_SCHEMA_PATH,
    canonical_json,
    sha256_digest,
    validate_against_schema,
)
from .errors import NarrativeRiskValidationError

VERSION = "2.0.0"
ENVIRONMENTS = {"development", "test", "staging", "production"}
CHECK_STATUSES = {"pass", "warn", "fail"}
SEVERITIES = {"info", "low", "medium", "high", "critical"}
POLICY_STATUSES = {"draft", "active", "retired"}
DELETION_MODES = {"archive_and_tombstone", "anonymize_then_archive", "legal_hold_only"}
RETENTION_CATEGORIES = (
    "case_metadata", "canonical_revisions", "review_events", "governance_records",
    "monitoring_records", "stakeholder_records", "comparative_records",
    "publication_records", "api_usage", "activity_log",
)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_datetime(value: str | None, field: str, *, required: bool = False) -> str | None:
    if value in (None, ""):
        if required:
            raise NarrativeRiskValidationError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NarrativeRiskValidationError(f"{field} must be an ISO 8601 date-time string") from exc
    if parsed.tzinfo is None:
        raise NarrativeRiskValidationError(f"{field} must include a timezone")
    return value


def urn(value: str | None, field: str) -> str:
    if value is None:
        return f"urn:uuid:{uuid4()}"
    if not isinstance(value, str) or not value.startswith("urn:uuid:"):
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier")
    try:
        UUID(value[9:])
    except (ValueError, AttributeError) as exc:
        raise NarrativeRiskValidationError(f"{field} must be a urn:uuid identifier") from exc
    return value.lower()


def text(value: Any, field: str, *, required: bool = False, maximum: int = 20000) -> str:
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


def choice(value: Any, field: str, allowed: Iterable[str], default: str | None = None) -> str:
    if value in (None, ""):
        if default is None:
            raise NarrativeRiskValidationError(f"{field} is required")
        return default
    if not isinstance(value, str):
        raise NarrativeRiskValidationError(f"{field} must be a string")
    cleaned = value.strip().lower()
    values = set(allowed)
    if cleaned not in values:
        raise NarrativeRiskValidationError(f"{field} must be one of: {', '.join(sorted(values))}")
    return cleaned


def _schema(label: str, value: Mapping[str, Any], path: Path) -> None:
    try:
        validate_against_schema(value, path)
    except Exception as exc:
        if exc.__class__.__module__.startswith("jsonschema"):
            raise NarrativeRiskValidationError(f"invalid {label}: {exc.message}") from exc
        raise


def _finalize(value: dict[str, Any], hash_field: str, path: Path, label: str) -> dict[str, Any]:
    value[hash_field] = sha256_digest({key: item for key, item in value.items() if key != hash_field})
    _schema(label, value, path)
    return value


def _check(check_id: str, category: str, status: str, severity: str, message: str, remediation: str = "") -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category,
        "status": choice(status, "status", CHECK_STATUSES),
        "severity": choice(severity, "severity", SEVERITIES),
        "message": text(message, "message", required=True, maximum=2000),
        "remediation": text(remediation, "remediation", maximum=4000),
    }


def build_security_readiness_report(
    config: Mapping[str, Any], *, generated_at: str | None = None,
    report_id: str | None = None, environment: str | None = None,
) -> dict[str, Any]:
    """Evaluate explicit deployment settings without reading or exposing secret values."""
    if not isinstance(config, Mapping):
        raise NarrativeRiskValidationError("config must be a JSON object")
    env = choice(environment or config.get("environment"), "environment", ENVIRONMENTS, "development")
    production = env == "production"
    checks: list[dict[str, Any]] = []

    def bool_check(check_id: str, category: str, enabled: bool, severity: str, message: str, remediation: str) -> None:
        status = "pass" if enabled else ("fail" if production else "warn")
        checks.append(_check(check_id, category, status, severity, message if enabled else f"Not configured: {message}", remediation))

    bool_check("debug_disabled", "application", not bool(config.get("debug", False)), "critical", "Debug mode is disabled.", "Disable debug mode and interactive exception pages outside local development.")
    bool_check("api_key_required", "authentication", bool(config.get("require_api_key", False)), "critical", "Private API routes require scoped API keys.", "Set NARRATIVE_RISK_REQUIRE_API_KEY=true and issue least-privilege keys.")
    admin_length = int(config.get("admin_token_length") or 0)
    bool_check("admin_token_strength", "authentication", admin_length >= 32, "critical", "The administrator bootstrap token is at least 32 characters.", "Configure a random administrator token of at least 32 characters and rotate it after bootstrap.")
    bool_check("https_enforced", "transport", bool(config.get("enforce_https", False)), "critical", "HTTPS is enforced by the application or trusted proxy.", "Redirect HTTP to HTTPS and configure trusted proxy headers correctly.")
    bool_check("secure_headers", "transport", bool(config.get("secure_headers", True)), "high", "Security response headers are enabled.", "Enable CSP, frame protection, MIME sniffing protection, and a strict referrer policy.")
    allowed_origins = config.get("allowed_origins") or []
    explicit_origins = isinstance(allowed_origins, Sequence) and not isinstance(allowed_origins, (str, bytes)) and bool(allowed_origins) and "*" not in allowed_origins
    bool_check("explicit_cors", "transport", explicit_origins, "high", "CORS uses an explicit origin allowlist.", "Set NARRATIVE_RISK_ALLOWED_ORIGINS to trusted HTTPS origins and never use a wildcard in production.")
    max_bytes = int(config.get("max_content_length") or 0)
    request_limit_ok = 1024 <= max_bytes <= 2 * 1024 * 1024
    bool_check("request_size_limit", "application", request_limit_ok, "high", "Request bodies are limited to two megabytes or less.", "Set MAX_CONTENT_LENGTH to a positive value no greater than 2097152 bytes.")
    db_path = str(config.get("database_path") or "")
    persistent = db_path not in {"", ":memory:"} and not db_path.startswith("file::memory:")
    bool_check("persistent_database", "persistence", persistent, "high", "A persistent database path is configured.", "Use an instance-directory SQLite database or a managed production database.")
    bool_check("backup_directory", "resilience", bool(config.get("backup_directory")), "high", "A dedicated backup directory is configured.", "Configure a protected backup destination outside the live database directory.")
    bool_check("retention_policy", "privacy", bool(config.get("retention_policy_configured", False)), "high", "An active privacy and retention policy is configured.", "Create and activate a retention policy before production use.")
    bool_check("encryption_at_rest", "privacy", bool(config.get("encryption_at_rest_attested", False)), "critical", "Encryption at rest is attested by the deployment operator.", "Use encrypted volumes or managed storage and document the attestation.")
    bool_check("secure_session_cookie", "application", bool(config.get("cookie_secure", False)), "high", "Session cookies are marked Secure.", "Set SESSION_COOKIE_SECURE=true and SESSION_COOKIE_SAMESITE=Strict or Lax.")

    weights = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
    readiness_score = round(100 * sum(weights[item["status"]] for item in checks) / len(checks))
    blocking = [item["check_id"] for item in checks if item["status"] == "fail" and item["severity"] in {"high", "critical"}]
    warnings = [item for item in checks if item["status"] == "warn"]
    status = "blocked" if blocking else "needs_attention" if warnings else "ready"
    if not production and status == "ready":
        status = "development_only"
    recommendations = [item["remediation"] for item in checks if item["status"] != "pass" and item["remediation"]]
    report = {
        "report_id": urn(report_id, "report_id"), "report_version": VERSION,
        "generated_at": validate_datetime(generated_at, "generated_at") or iso_now(),
        "environment": env, "status": status, "readiness_score": readiness_score,
        "checks": checks, "blocking_check_ids": blocking, "recommendations": recommendations,
        "report_sha256": "",
    }
    return _finalize(report, "report_sha256", SECURITY_REPORT_SCHEMA_PATH, "security readiness report")


def normalize_privacy_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise NarrativeRiskValidationError("privacy policy must be a JSON object")
    allowed = {"policy_id", "name", "status", "default_retention_days", "retention_days", "deletion_mode", "legal_hold", "review_frequency_days", "created_at", "updated_at", "created_by", "notes"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise NarrativeRiskValidationError(f"unsupported privacy policy field(s): {', '.join(unknown)}")
    default_days = int(payload.get("default_retention_days", 2555))
    if not 1 <= default_days <= 36500:
        raise NarrativeRiskValidationError("default_retention_days must be between 1 and 36500")
    raw_retention = payload.get("retention_days") or {}
    if not isinstance(raw_retention, Mapping):
        raise NarrativeRiskValidationError("retention_days must be a JSON object")
    unknown_categories = sorted(set(raw_retention) - set(RETENTION_CATEGORIES))
    if unknown_categories:
        raise NarrativeRiskValidationError(f"unsupported retention category: {', '.join(unknown_categories)}")
    retention = {}
    for category in RETENTION_CATEGORIES:
        days = int(raw_retention.get(category, default_days))
        if not 1 <= days <= 36500:
            raise NarrativeRiskValidationError(f"retention_days.{category} must be between 1 and 36500")
        retention[category] = days
    created_at = validate_datetime(payload.get("created_at"), "created_at") or iso_now()
    updated_at = validate_datetime(payload.get("updated_at"), "updated_at") or created_at
    policy = {
        "policy_id": urn(payload.get("policy_id"), "policy_id"), "policy_version": VERSION,
        "name": text(payload.get("name", "Narrative Risk Retention Policy"), "name", required=True, maximum=500),
        "status": choice(payload.get("status"), "status", POLICY_STATUSES, "draft"),
        "default_retention_days": default_days, "retention_days": retention,
        "deletion_mode": choice(payload.get("deletion_mode"), "deletion_mode", DELETION_MODES, "archive_and_tombstone"),
        "legal_hold": bool(payload.get("legal_hold", False)),
        "review_frequency_days": int(payload.get("review_frequency_days", 365)),
        "created_at": created_at, "updated_at": updated_at,
        "created_by": text(payload.get("created_by"), "created_by", maximum=500) or None,
        "notes": text(payload.get("notes"), "notes", maximum=10000),
        "policy_sha256": "",
    }
    if not 1 <= policy["review_frequency_days"] <= 3650:
        raise NarrativeRiskValidationError("review_frequency_days must be between 1 and 3650")
    return _finalize(policy, "policy_sha256", PRIVACY_POLICY_SCHEMA_PATH, "privacy policy")


def _record_counts(case_detail: Mapping[str, Any]) -> dict[str, int]:
    return {
        "case_metadata": 1,
        "canonical_revisions": len(case_detail.get("revisions", [])),
        "review_events": len(case_detail.get("review_events", [])),
        "governance_records": (1 if case_detail.get("governance_workflow") else 0) + len(case_detail.get("review_assignments", [])) + len(case_detail.get("governance_decisions", [])),
        "monitoring_records": len(case_detail.get("monitoring_snapshots", [])) + len(case_detail.get("monitoring_comparisons", [])) + len(case_detail.get("watchlists", [])) + len(case_detail.get("monitoring_alerts", [])) + len(case_detail.get("site_intelligence_events", [])),
        "stakeholder_records": len(case_detail.get("stakeholder_actors", [])) + len(case_detail.get("stakeholder_relationships", [])) + len(case_detail.get("stakeholder_incentives", [])) + len(case_detail.get("stakeholder_pressures", [])) + len(case_detail.get("stakeholder_consequences", [])),
        "comparative_records": len(case_detail.get("comparison_sets", [])) + len(case_detail.get("comparative_evidence_matrices", [])) + len(case_detail.get("scenarios", [])) + len(case_detail.get("scenario_results", [])) + len(case_detail.get("sensitivity_analyses", [])) + len(case_detail.get("decision_studio_handoffs", [])),
        "publication_records": len(case_detail.get("publication_briefings", [])) + len(case_detail.get("publication_packages", [])) + len(case_detail.get("public_embeds", [])) + len(case_detail.get("platform_handoffs", [])),
        "api_usage": 0,
        "activity_log": len(case_detail.get("activity", [])),
    }


def build_retention_assessment(
    case_detail: Mapping[str, Any], policy: Mapping[str, Any], *, assessed_at: str | None = None,
    assessment_id: str | None = None, assessed_by: str | None = None,
) -> dict[str, Any]:
    _schema("privacy policy", policy, PRIVACY_POLICY_SCHEMA_PATH)
    if not isinstance(case_detail, Mapping) or not case_detail.get("case_id"):
        raise NarrativeRiskValidationError("case_detail must contain case_id")
    timestamp = validate_datetime(assessed_at, "assessed_at") or iso_now()
    now = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    basis_value = case_detail.get("archived_at") or case_detail.get("updated_at") or case_detail.get("created_at")
    basis = datetime.fromisoformat(validate_datetime(basis_value, "case retention basis", required=True).replace("Z", "+00:00"))
    counts = _record_counts(case_detail)
    categories=[]
    due=[]
    for category in RETENTION_CATEGORIES:
        days=int(policy["retention_days"][category])
        due_at=(basis+timedelta(days=days)).isoformat()
        is_due=now >= basis+timedelta(days=days) and counts[category] > 0
        item={"category":category,"record_count":counts[category],"retention_days":days,"basis_at":basis_value,"due_at":due_at,"due":is_due}
        categories.append(item)
        if is_due: due.append(category)
    if policy.get("legal_hold"):
        status="legal_hold"
        recommended=["Preserve all records until the documented legal hold is released."]
    elif due:
        status="action_required"
        recommended=[f"Apply the approved {policy['deletion_mode']} workflow to due categories.", "Record authorized disposition before deleting or anonymizing any data."]
    else:
        status="current"
        recommended=["Reassess retention after the next material case update or policy review."]
    assessment={
        "assessment_id":urn(assessment_id,"assessment_id"),"assessment_version":VERSION,
        "case_id":case_detail["case_id"],"policy_id":policy["policy_id"],
        "policy_snapshot":deepcopy(dict(policy)),"assessed_at":timestamp,
        "assessed_by":text(assessed_by,"assessed_by",maximum=500) or None,
        "status":status,"record_counts":counts,"categories":categories,
        "due_categories":due,"recommended_actions":recommended,"assessment_sha256":"",
    }
    return _finalize(assessment,"assessment_sha256",RETENTION_ASSESSMENT_SCHEMA_PATH,"retention assessment")


def _file_sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_inspection(path: Path) -> tuple[str, int, dict[str, int], str | None]:
    connection=sqlite3.connect(str(path))
    try:
        integrity=str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys=len(connection.execute("PRAGMA foreign_key_check").fetchall())
        tables=[row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts={name:int(connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]) for name in tables}
        row=connection.execute("SELECT value FROM workspace_meta WHERE key='schema_version'").fetchone() if "workspace_meta" in tables else None
        schema_version=row[0] if row else None
        return integrity,foreign_keys,counts,schema_version
    finally:
        connection.close()


def create_sqlite_backup(
    database_path: str | Path, destination_path: str | Path, *, created_at: str | None = None,
    created_by: str | None = None, backup_id: str | None = None,
) -> dict[str, Any]:
    source=Path(database_path).expanduser().resolve()
    destination=Path(destination_path).expanduser().resolve()
    if str(database_path)==":memory:" or not source.exists():
        raise NarrativeRiskValidationError("a persistent existing SQLite database is required for backup")
    if source == destination:
        raise NarrativeRiskValidationError("backup destination must differ from the live database")
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise NarrativeRiskValidationError(f"backup destination already exists: {destination}")
    source_connection=sqlite3.connect(str(source))
    backup_connection=sqlite3.connect(str(destination))
    try:
        source_connection.backup(backup_connection)
        backup_connection.commit()
    finally:
        backup_connection.close(); source_connection.close()
    integrity,foreign_keys,counts,schema_version=_database_inspection(destination)
    timestamp=validate_datetime(created_at,"created_at") or iso_now()
    manifest={
        "backup_id":urn(backup_id,"backup_id"),"backup_version":VERSION,
        "source_database":str(source),"backup_path":str(destination),"created_at":timestamp,
        "created_by":text(created_by,"created_by",maximum=500) or None,
        "source_size_bytes":source.stat().st_size,"backup_size_bytes":destination.stat().st_size,
        "database_sha256":_file_sha256(destination),"integrity_check":integrity,
        "foreign_key_violation_count":foreign_keys,"table_counts":counts,
        "schema_version":schema_version,"verified_at":timestamp,"manifest_sha256":"",
    }
    return _finalize(manifest,"manifest_sha256",BACKUP_MANIFEST_SCHEMA_PATH,"backup manifest")


def verify_sqlite_backup(manifest: Mapping[str, Any], *, verified_at: str | None = None) -> dict[str, Any]:
    _schema("backup manifest",manifest,BACKUP_MANIFEST_SCHEMA_PATH)
    expected=sha256_digest({key:value for key,value in manifest.items() if key!="manifest_sha256"})
    path=Path(str(manifest["backup_path"]))
    if expected != manifest["manifest_sha256"]:
        raise NarrativeRiskValidationError("backup manifest hash mismatch")
    if not path.exists():
        raise NarrativeRiskValidationError(f"backup file does not exist: {path}")
    integrity,foreign_keys,counts,schema_version=_database_inspection(path)
    report={
        "backup_id":manifest["backup_id"],"verified_at":validate_datetime(verified_at,"verified_at") or iso_now(),
        "file_exists":True,"hash_match":_file_sha256(path)==manifest["database_sha256"],
        "size_match":path.stat().st_size==manifest["backup_size_bytes"],
        "integrity_check":integrity,"foreign_key_violation_count":foreign_keys,
        "table_counts_match":counts==manifest["table_counts"],"schema_version_match":schema_version==manifest.get("schema_version"),
    }
    report["verified"]=all([report["hash_match"],report["size_match"],integrity=="ok",foreign_keys==0,report["table_counts_match"],report["schema_version_match"]])
    return report


def restore_sqlite_backup(manifest: Mapping[str, Any], target_path: str | Path, *, overwrite: bool = False) -> dict[str, Any]:
    verification=verify_sqlite_backup(manifest)
    if not verification["verified"]:
        raise NarrativeRiskValidationError("backup verification failed; restore is blocked")
    target=Path(target_path).expanduser().resolve()
    source=Path(str(manifest["backup_path"])).expanduser().resolve()
    if target.exists() and not overwrite:
        raise NarrativeRiskValidationError(f"restore target already exists: {target}")
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): target.unlink()
    source_connection=sqlite3.connect(str(source)); target_connection=sqlite3.connect(str(target))
    try:
        source_connection.backup(target_connection); target_connection.commit()
    finally:
        target_connection.close(); source_connection.close()
    integrity,foreign_keys,counts,schema_version=_database_inspection(target)
    return {"restored":integrity=="ok" and foreign_keys==0,"target_path":str(target),"database_sha256":_file_sha256(target),"integrity_check":integrity,"foreign_key_violation_count":foreign_keys,"table_counts":counts,"schema_version":schema_version}


def audit_wordpress_accessibility(plugin_root: str | Path, *, generated_at: str | None = None, report_id: str | None = None) -> dict[str, Any]:
    root=Path(plugin_root).expanduser().resolve()
    php=root/"catalyst-narrative-risk-demo.php"
    assets=root/"assets"
    if not php.exists() or not assets.exists():
        raise NarrativeRiskValidationError("plugin_root must contain the Catalyst Narrative Risk WordPress plugin")
    php_text=php.read_text(encoding="utf-8")
    css_text="\n".join(path.read_text(encoding="utf-8") for path in sorted(assets.glob("*.css")))
    js_text="\n".join(path.read_text(encoding="utf-8") for path in sorted(assets.glob("*.js")))
    button_count=len(re.findall(r"<button\b",php_text,re.I))
    typed_buttons=len(re.findall(r"<button\b[^>]*\btype=",php_text,re.I))
    controls=len(re.findall(r"<(?:input|select|textarea)\b",php_text,re.I))
    labels=len(re.findall(r"<label\b",php_text,re.I))
    tests=[
        ("live_regions","semantics","aria-live" in php_text,"high","Dynamic status output uses an ARIA live region.","Add aria-live=polite to status and result containers."),
        ("alert_role","semantics",'role="alert"' in php_text,"high","Errors are announced with role=alert.","Add role=alert to visible validation messages."),
        ("section_labels","semantics","aria-labelledby" in php_text,"medium","Complex workspace sections have accessible names.","Use aria-labelledby on major workspace sections."),
        ("button_types","keyboard",button_count==typed_buttons,"high","Every button declares its type.","Add type=button or type=submit to every button."),
        ("form_labels","semantics",labels>=controls,"high","Form controls are associated with visible labels.","Wrap controls in labels or use matching for/id attributes."),
        ("focus_visible","keyboard",":focus-visible" in css_text,"critical","Keyboard focus has a visible focus indicator.","Add a high-contrast :focus-visible outline for links, buttons, and form controls."),
        ("reduced_motion","motion","prefers-reduced-motion" in css_text,"medium","Reduced-motion preferences are respected.","Disable transitions and animations under prefers-reduced-motion: reduce."),
        ("responsive_layout","responsive","@media" in css_text,"medium","The interface includes responsive breakpoints.","Add narrow-screen layout rules."),
        ("no_inline_handlers","security",not re.search(r"\son(?:click|change|submit)=",php_text,re.I),"medium","Markup avoids inline event handlers.","Bind events from enqueued JavaScript instead of inline handlers."),
        ("no_positive_tabindex","keyboard",not re.search(r"tabindex=[\"']?[1-9]",php_text,re.I),"high","Markup does not impose a positive tabindex order.","Use document order and tabindex=0 only when necessary."),
        ("js_keyboard_safe","keyboard","keyCode" not in js_text,"low","JavaScript avoids deprecated keyCode handling.","Use KeyboardEvent.key when keyboard logic is required."),
    ]
    checks=[_check(cid,cat,"pass" if passed else "fail",sev,msg,rem) for cid,cat,passed,sev,msg,rem in tests]
    score=round(100*sum(item["status"]=="pass" for item in checks)/len(checks))
    status="fail" if any(item["status"]=="fail" and item["severity"] in {"critical","high"} for item in checks) else "warn" if any(item["status"]=="fail" for item in checks) else "pass"
    report={"report_id":urn(report_id,"report_id"),"report_version":VERSION,"generated_at":validate_datetime(generated_at,"generated_at") or iso_now(),"plugin_root":str(root),"status":status,"score":score,"control_count":controls,"label_count":labels,"button_count":button_count,"typed_button_count":typed_buttons,"checks":checks,"report_sha256":""}
    return _finalize(report,"report_sha256",ACCESSIBILITY_REPORT_SCHEMA_PATH,"accessibility report")


def build_performance_report(repository: Any, *, case_id: str | None = None, generated_at: str | None = None, report_id: str | None = None, budgets: Mapping[str, Any] | None = None) -> dict[str, Any]:
    limits={"health_ms":100.0,"list_cases_ms":250.0,"bundle_ms":1000.0,"bundle_bytes":5_000_000,"database_bytes":250_000_000}
    if budgets:
        for key,value in budgets.items():
            if key not in limits: raise NarrativeRiskValidationError(f"unsupported performance budget: {key}")
            limits[key]=float(value)
    start=time.perf_counter(); repository.health(); health_ms=(time.perf_counter()-start)*1000
    start=time.perf_counter(); cases=repository.list_cases(limit=100,offset=0); list_ms=(time.perf_counter()-start)*1000
    bundle_ms=0.0; bundle_bytes=0
    if case_id:
        start=time.perf_counter(); bundle=repository.export_case_bundle(case_id); bundle_ms=(time.perf_counter()-start)*1000; bundle_bytes=len(canonical_json(bundle).encode("utf-8"))
    db_bytes=0
    path=str(getattr(repository,"database_path",":memory:"))
    if path != ":memory:" and Path(path).exists(): db_bytes=Path(path).stat().st_size
    metrics=[
        {"metric":"health_ms","value":round(health_ms,3),"budget":limits["health_ms"],"unit":"ms"},
        {"metric":"list_cases_ms","value":round(list_ms,3),"budget":limits["list_cases_ms"],"unit":"ms"},
        {"metric":"bundle_ms","value":round(bundle_ms,3),"budget":limits["bundle_ms"],"unit":"ms"},
        {"metric":"bundle_bytes","value":bundle_bytes,"budget":limits["bundle_bytes"],"unit":"bytes"},
        {"metric":"database_bytes","value":db_bytes,"budget":limits["database_bytes"],"unit":"bytes"},
    ]
    for metric in metrics: metric["status"]="pass" if metric["value"]<=metric["budget"] else "fail"
    status="fail" if any(item["status"]=="fail" for item in metrics) else "pass"
    report={"report_id":urn(report_id,"report_id"),"report_version":VERSION,"generated_at":validate_datetime(generated_at,"generated_at") or iso_now(),"status":status,"case_count_sampled":len(cases),"case_id":case_id,"metrics":metrics,"report_sha256":""}
    return _finalize(report,"report_sha256",PERFORMANCE_REPORT_SCHEMA_PATH,"performance report")


def build_production_readiness_report(*, security_report: Mapping[str, Any], accessibility_report: Mapping[str, Any], performance_report: Mapping[str, Any], database_diagnostics: Mapping[str, Any], backup_verification: Mapping[str, Any] | None = None, generated_at: str | None = None, report_id: str | None = None) -> dict[str, Any]:
    _schema("security readiness report",security_report,SECURITY_REPORT_SCHEMA_PATH)
    _schema("accessibility report",accessibility_report,ACCESSIBILITY_REPORT_SCHEMA_PATH)
    _schema("performance report",performance_report,PERFORMANCE_REPORT_SCHEMA_PATH)
    backup_ok=bool(backup_verification and backup_verification.get("verified"))
    db_ok=database_diagnostics.get("integrity_check")=="ok" and int(database_diagnostics.get("foreign_key_violation_count",1))==0
    blockers=[]
    if security_report["status"]=="blocked": blockers.append("security_readiness")
    if accessibility_report["status"]=="fail": blockers.append("accessibility")
    if performance_report["status"]=="fail": blockers.append("performance")
    if not db_ok: blockers.append("database_integrity")
    if blockers: status="blocked"
    elif not backup_ok: status="needs_attention"
    else: status="ready"
    report={
        "report_id":urn(report_id,"report_id"),"report_version":VERSION,
        "generated_at":validate_datetime(generated_at,"generated_at") or iso_now(),"status":status,
        "blocking_domains":blockers,"backup_verified":backup_ok,"database_integrity_ok":db_ok,
        "security_report":deepcopy(dict(security_report)),"accessibility_report":deepcopy(dict(accessibility_report)),
        "performance_report":deepcopy(dict(performance_report)),"database_diagnostics":deepcopy(dict(database_diagnostics)),
        "report_sha256":"",
    }
    return _finalize(report,"report_sha256",PRODUCTION_READINESS_SCHEMA_PATH,"production readiness report")
