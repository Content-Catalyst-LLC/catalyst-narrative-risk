def score_simple_risk(holdings, cash, total):
    if total <= 0:
        return {"score": 0, "level": "Low", "concentration": 0.0,
                "symbols_count": 0, "cash_buffer": 1.0, "notes": "No assets"}
    largest = holdings[0]["value"] if holdings else 0.0
    concentration = largest / total
    symbols_count = len(holdings)
    cash_buffer = cash / total
    pts = 0
    if concentration >= 0.60: pts += 35
    elif concentration >= 0.40: pts += 25
    elif concentration >= 0.25: pts += 15
    elif concentration >= 0.15: pts += 8
    if symbols_count <= 1: pts += 20
    elif symbols_count == 2: pts += 12
    elif symbols_count <= 4: pts += 6
    if cash_buffer < 0.05: pts += 20
    elif cash_buffer < 0.10: pts += 12
    elif cash_buffer < 0.20: pts += 6
    pts = max(0, min(100, pts))
    level = "High" if pts >= 60 else ("Medium" if pts >= 30 else "Low")
    notes = []
    if concentration >= 0.40: notes.append("High position concentration")
    if symbols_count <= 2: notes.append("Low diversification")
    if cash_buffer < 0.10: notes.append("Low cash buffer")
    if not notes: notes.append("Balanced by heuristics")
    return {
        "score": pts, "level": level, "concentration": concentration,
        "symbols_count": symbols_count, "cash_buffer": cash_buffer,
        "notes": "; ".join(notes)
    }
