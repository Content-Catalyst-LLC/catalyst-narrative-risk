"""Shared exceptions for Catalyst Narrative Risk."""


class NarrativeRiskValidationError(ValueError):
    """Raised when a narrative-risk payload cannot be normalized safely."""
