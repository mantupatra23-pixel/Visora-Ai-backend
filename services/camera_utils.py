# services/camera_utils.py
import math, json, uuid, time
from pathlib import Path
ROOT = Path(".").resolve()

def _tid(): return uuid.uuid4().hex[:8]

# simple emotional->shot mapping
EMOTIONAL_MAP = {
  "tense":["close_up","dutch","handheld"],
  "romantic":["close_up","soft_dof","slow_push"],
  "epic":["wide","drone_orbit","crane"],
  "dialogue":["over_shoulder","medium","two_shot"],
  "action":["car_follow","handheld","tracking","cut_to_close"]
}

def parse_intent(text: str):
    t = text.lower()
    # basic heuristics; extendable with ML later
    if any(w in t for w in ["fight","explode","chase","punch","kick","run","battle"]):
        mood = "action"
    elif any(w in t for w in ["kiss","love","romantic","romance","hug","tear"]):
        mood = "romantic"
    elif any(w in t for w in ["sad","cry","loss","lonely","sorrow"]):
        mood = "tense"
    elif any(w in t for w in ["epic","grand","vast","panoramic","hero"]):
        mood = "epic"
    elif any(w in t for w in ["talk","dialogue","says","asks","reply","answer"]):
        mood = "dialogue"
    else:
        mood = "dialogue"
    return {"mood":mood}

def build_shot_list(script_text: str, length_sec: int = 12, fps: int = 24):
    parsed = parse_intent(script_text)
    mood = parsed["mood"]
    shots = EMOTIONAL_MAP.get(mood, ["medium"])
    # create timeline: each shot gets frames
    total_frames = length_sec * fps
    per_shot = max(8, int(total_frames / max(1,len(shots))))
    timeline = []
    cur = 1
    for s in shots:
        duration = per_shot
        timeline.append({"shot": s, "start_frame": cur, "frames": duration})
        cur += duration
    # if leftover frames distribute to last
    if cur <= total_frames:
        timeline[-1]["frames"] += (total_frames - cur + 1)
    return {"mood":mood,"total_frames":total_frames,"timeline":timeline}
