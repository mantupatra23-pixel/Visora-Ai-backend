from flask import Blueprint, request, jsonify

video_bp = Blueprint("video", __name__)

@video_bp.post("/make")
def make_video():
    output = "static/outputs/final_video.mp4"
    return jsonify({"ok": True, "output": output})
