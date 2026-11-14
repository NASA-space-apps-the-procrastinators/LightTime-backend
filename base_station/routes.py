from flask import Blueprint, jsonify

bp = Blueprint("base", __name__)


@bp.get("/health")
def health():
    return jsonify(ok=True)
