"""Deprecated compatibility helpers isolated from the narrative-risk engine."""

from __future__ import annotations

from typing import Any


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def score_simple_risk(holdings: list[dict[str, Any]], cash: float, total: float) -> dict[str, Any]:
    """Legacy portfolio-risk shim retained only for downstream compatibility."""
    if total <= 0:
        return {
            "score": 0,
            "level": "Low",
            "concentration": 0.0,
            "symbols_count": 0,
            "cash_buffer": 1.0,
            "notes": "No assets",
        }
    largest = holdings[0]["value"] if holdings else 0.0
    concentration = largest / total
    symbols_count = len(holdings)
    cash_buffer = cash / total
    points = 0
    if concentration >= 0.60:
        points += 35
    elif concentration >= 0.40:
        points += 25
    elif concentration >= 0.25:
        points += 15
    elif concentration >= 0.15:
        points += 8
    if symbols_count <= 1:
        points += 20
    elif symbols_count == 2:
        points += 12
    elif symbols_count <= 4:
        points += 6
    if cash_buffer < 0.05:
        points += 20
    elif cash_buffer < 0.10:
        points += 12
    elif cash_buffer < 0.20:
        points += 6
    points = _clamp(points)
    level = "High" if points >= 60 else ("Medium" if points >= 30 else "Low")
    notes = []
    if concentration >= 0.40:
        notes.append("High position concentration")
    if symbols_count <= 2:
        notes.append("Low diversification")
    if cash_buffer < 0.10:
        notes.append("Low cash buffer")
    if not notes:
        notes.append("Balanced by heuristics")
    return {
        "score": points,
        "level": level,
        "concentration": concentration,
        "symbols_count": symbols_count,
        "cash_buffer": cash_buffer,
        "notes": "; ".join(notes),
    }
