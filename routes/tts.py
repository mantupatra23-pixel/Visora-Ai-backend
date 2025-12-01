from flask import Blueprint, request, jsonify

tts_bp = Blueprint("tts", __name__)

@tts_bp.post("/speak")
def speak():
    data = request.json or {}
    text = data.get("text", "")
    filename = "static/outputs/fake_tts.wav"
    return jsonify({"ok": True, "file": filename, "text": text})
