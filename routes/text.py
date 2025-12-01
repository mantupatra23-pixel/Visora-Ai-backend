from flask import Blueprint, request, jsonify

text_bp = Blueprint("text", __name__)

@text_bp.post("/generate")
def generate_text():
    data = request.json or {}
    prompt = data.get("prompt", "")
    story = f"Generated story for: {prompt}"
    return jsonify({"ok": True, "story": story})
