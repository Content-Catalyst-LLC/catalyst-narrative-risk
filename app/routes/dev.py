from flask import Blueprint, request, jsonify
from app.services.claims.pe_multiple import make_pe_positioning_claim

bp = Blueprint("dev", __name__, url_prefix="/dev")

@bp.get("/claims/pe")
def gen_pe_claim():
    ticker = request.args.get("ticker", "AAPL")
    asof = request.args.get("asof")
    return jsonify(make_pe_positioning_claim(ticker, asof)), 200
