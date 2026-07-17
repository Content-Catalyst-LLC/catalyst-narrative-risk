"""Contract, schema, canonicalization, and hashing utilities."""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.1.0"
CONTRACT_PATH = ROOT / "contracts" / "narrative-risk-contract.v1.1.0.json"
VOCABULARIES_PATH = ROOT / "contracts" / "controlled-vocabularies.v1.1.0.json"
METHOD_PATH = ROOT / "methods" / "transparent-heuristic.v1.1.0.json"
INPUT_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_input.schema.json"
METHOD_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_method_snapshot.schema.json"
RECORD_SCHEMA_PATH = ROOT / "schemas" / "narrative_risk_record.schema.json"
LEGACY_RECORD_SCHEMA_PATH = ROOT / "schemas" / "archive" / "narrative_risk_record.v1.0.1.schema.json"


@lru_cache(maxsize=None)
def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_definition() -> dict[str, Any]:
    return json.loads(json.dumps(load_json(CONTRACT_PATH)))


def controlled_vocabularies() -> dict[str, Any]:
    return json.loads(json.dumps(load_json(VOCABULARIES_PATH)))


def current_method_snapshot() -> dict[str, Any]:
    return json.loads(json.dumps(load_json(METHOD_PATH)))


def _canonical_value(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    return value


def canonical_json(value: Any) -> str:
    """Return the cross-runtime canonical JSON representation used for digests."""
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _registry():
    try:
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("referencing is required to validate narrative-risk schemas") from exc

    schemas = [
        load_json(INPUT_SCHEMA_PATH),
        load_json(METHOD_SCHEMA_PATH),
        load_json(RECORD_SCHEMA_PATH),
        load_json(LEGACY_RECORD_SCHEMA_PATH),
    ]
    registry = Registry()
    for schema in schemas:
        schema_id = schema.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return registry


def validate_against_schema(value: Mapping[str, Any], schema_path: Path) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("jsonschema is required to validate narrative-risk records") from exc

    schema = load_json(schema_path)
    validator = Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    validator.validate(dict(value))
