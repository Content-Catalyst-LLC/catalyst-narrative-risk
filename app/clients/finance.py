import os
from typing import Optional, Dict, Any
import requests

FINANCE_API_URL = os.getenv("FINANCE_API_URL", "http://127.0.0.1:5000")

def fetch_pe_scenarios(ticker: str, asof: Optional[str] = None) -> Dict[str, Any]:
    params = {"ticker": ticker}
    if asof:
        params["asof"] = asof
    r = requests.get(f"{FINANCE_API_URL}/v1/scenarios/pe", params=params, timeout=10)
    r.raise_for_status()
    return r.json()
