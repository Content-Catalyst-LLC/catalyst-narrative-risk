from typing import Optional, Dict, Any
from app.clients.finance import fetch_pe_scenarios

def make_pe_positioning_claim(ticker: str, asof: Optional[str] = None) -> Dict[str, Any]:
    data = fetch_pe_scenarios(ticker, asof)
    cur  = data.get("current_pe")
    bear = data.get("bear",{}).get("pe")
    base = data.get("base",{}).get("pe")
    bull = data.get("bull",{}).get("pe")
    prov = data.get("provenance_id")
    asof = data.get("asof")
    text = (f"{ticker} trades at {cur}x earnings. "
            f"P/E potential bands: {bear}x (bear), {base}x (base), {bull}x (bull). "
            f"Multiple expansion/compression is assessed against these bands.")
    return {
        "category": "valuation-multiple",
        "text": text,
        "evidence": [{
            "source": "catalyst-finance",
            "metric": "pe_potential",
            "ticker": ticker,
            "asof": asof,
            "value": {"current_pe": cur, "bear": bear, "base": base, "bull": bull},
            "provenance_id": prov
        }],
        "footnotes": [f"Catalyst Finance v1, as of {asof}."]
    }
