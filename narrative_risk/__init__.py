from .legacy import score_simple_risk
from .service import (
    METHOD,
    RECORD_TYPE,
    SCHEMA_VERSION,
    VERSION,
    NarrativeRiskInput,
    NarrativeRiskValidationError,
    build_narrative_risk_record,
    normalize_narrative_risk_input,
    score_narrative_risk,
    validate_narrative_risk_record,
)

__all__ = [
    "METHOD",
    "RECORD_TYPE",
    "SCHEMA_VERSION",
    "VERSION",
    "NarrativeRiskInput",
    "NarrativeRiskValidationError",
    "build_narrative_risk_record",
    "normalize_narrative_risk_input",
    "score_narrative_risk",
    "validate_narrative_risk_record",
    "score_simple_risk",
]
