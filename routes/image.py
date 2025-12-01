from flask import Blueprint, request, jsonify

image_bp = Blueprint("image", __name__)

@image_bp.post("/generate")
def generate_image():
    data = request.json or {}
    prompt = data.get("prompt", "")
    img = "static/outputs/fake_image.png"
    return jsonify({"ok": True, "image": img, "prompt": prompt})
