from flask import Blueprint, request, jsonify

auto_bp = Blueprint("auto", __name__)

@auto_bp.post("/create")
def auto_create():
    data = request.json or {}
    prompt = data.get("prompt", "")
    return jsonify({"ok": True, "message": "Auto pipeline started", "prompt": prompt})
