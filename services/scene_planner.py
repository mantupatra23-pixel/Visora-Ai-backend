# services/scene_planner.py
"""
Scene Layout / Auto-Storyboarding Engine
- Input: script_text (with optional speaker tags), scene_settings (location, mood, num_cameras)
- Output:
    - scene_graph: characters, props, environment nodes
    - shot_list: ordered shots with shot_type, camera_params, duration_hint, framing, notes
    - blocking: per-shot character positions and actions
    - lighting_presets: suggested lights per shot
    - storyboard_frames: simple JSON thumbnails hints (frame description, focus area)
- Designed to be deterministic and editable. Can be extended to call an LLM for richer variations.
"""

import re
import uuid
from typing import List, Dict, Any
from pathlib import Path
import math

ROOT = Path(".").resolve()

def _task_id():
    return uuid.uuid4().hex[:10]

# Helper heuristics
SHOT_TYPES = [
    "establishing_wide",
    "wide",
    "medium",
    "medium_closeup",
    "closeup",
    "two_shot",
    "over_shoulder",
    "insert",
    "reaction",
    "cutaway",
    "dramatic_push"
]

CAMERA_PRESETS = {
    "establishing_wide": {"fov": 45, "distance": 15, "angle":"eye"},
    "wide": {"fov": 50, "distance": 10, "angle":"eye"},
    "medium": {"fov": 35, "distance": 6, "angle":"eye"},
    "medium_closeup": {"fov": 28, "distance": 3.5, "angle":"eye"},
    "closeup": {"fov": 25, "distance": 1.5, "angle":"eye"},
    "two_shot": {"fov": 35, "distance": 5, "angle":"eye"},
    "over_shoulder": {"fov": 40, "distance": 4, "angle":"over_shoulder"},
    "insert": {"fov": 20, "distance": 0.8, "angle":"macro"},
    "reaction": {"fov": 30, "distance": 2.0, "angle":"eye"},
    "cutaway": {"fov": 50, "distance": 8, "angle":"eye"},
    "dramatic_push": {"fov": 22, "distance": 2.0, "angle":"slow_push"}
}

DEFAULT_LIGHTING = {
    "day": {"key":"sun_45", "fill":"soft_white", "rim":"soft_orange"},
    "night": {"key":"spot_cool", "fill":"low_blue", "rim":"edge_blue"},
    "interior": {"key":"tungsten_key", "fill":"warm_fill", "rim":"warm_back"}
}

def parse_script_to_lines(script_text: str) -> List[Dict]:
    """
    Parse simple script format with lines like:
      Character: Dialogue...
    or plain sentences. Return list of segments with speaker (optional) and text.
    """
    lines = []
    for raw in re.split(r'\n+', script_text.strip()):
        if not raw.strip(): continue
        m = re.match(r'^\s*([A-Za-z0-9_ \-]+)\s*:\s*(.+)', raw)
        if m:
            speaker = m.group(1).strip()
            text = m.group(2).strip()
        else:
            speaker = None
            text = raw.strip()
        lines.append({"speaker": speaker, "text": text})
    return lines

def estimate_line_duration(text: str, wpm: int = 140) -> float:
    words = len(re.findall(r'\w+', text))
    sec_per_word = 60.0 / wpm
    return max(0.25, round(words * sec_per_word, 3))

def pick_shot_for_line(line_idx:int, total_lines:int, speaker: str|None, prev_shot: str|None) -> str:
    """
    Simple heuristic to pick shot type:
    - first line -> establishing_wide
    - if speaker changed -> over_shoulder / two_shot
    - short exclamations -> closeup/reaction
    - else alternate medium/closeups
    """
    if line_idx == 0:
        return "establishing_wide"
    if speaker and speaker.lower().startswith("old") or (speaker and "old" in speaker.lower()):
        # older character -> give medium_closeup occasional
        return "medium_closeup"
    if prev_shot is None:
        return "medium"
    # if speaker changes often, use two_shot/over_shoulder
    if line_idx % 5 == 0:
        return "two_shot"
    # reaction on short lines
    if len(line_idx.__str__())<3:  # fallback meaningless; prefer text length
        pass
    # length-based
    return "medium_closeup" if (line_idx % 3==0) else "medium"

def analyze_scene(script_text: str, env: Dict[str,Any] = None, characters: List[Dict]=None, mood:str="day", num_cameras:int=3) -> Dict:
    """
    Main planner entry.
    characters: optional list of {name, model, default_persona}
    env: optional dict like {location: "jungle", props: ["rock","tree"], time:"day"}
    """
    env = env or {}
    characters = characters or []
    lines = parse_script_to_lines(script_text)
    shots = []
    scene_graph = {
        "environment": env.get("location","default_set"),
        "time": env.get("time", mood),
        "props": env.get("props", []),
        "characters": characters
    }
    prev_shot = None
    time_cursor = 0.0
    for idx, seg in enumerate(lines):
        dur = estimate_line_duration(seg["text"])
        shot_type = pick_shot_for_line(idx, len(lines), seg["speaker"], prev_shot)
        cam = CAMERA_PRESETS.get(shot_type, CAMERA_PRESETS["medium"])
        # blocking: position characters on X axis based on name hashing
        blocking = []
        if characters:
            for i,ch in enumerate(characters):
                xpos = -2 + i*2  # spread
                zpos = 0
                facing = "center" if seg["speaker"]==ch.get("name") else "towards_"+(seg["speaker"] or "center")
                blocking.append({"character": ch.get("name"), "x": xpos, "z": zpos, "facing": facing})
        else:
            # derive simple blocking from speaker
            if seg["speaker"]:
                blocking.append({"character": seg["speaker"], "x":0, "z":0, "facing":"center"})
        # lighting
        lighting = DEFAULT_LIGHTING.get(env.get("time","day"), DEFAULT_LIGHTING["day"])
        shot = {
            "index": idx,
            "type": shot_type,
            "camera": cam,
            "duration_hint": round(dur,3),
            "start_time": round(time_cursor,3),
            "end_time": round(time_cursor + dur,3),
            "speaker": seg.get("speaker"),
            "text": seg.get("text"),
            "blocking": blocking,
            "lighting": lighting,
            "notes": f"Auto-shot for line {idx} ({shot_type})"
        }
        shots.append(shot)
        prev_shot = shot_type
        time_cursor += dur
        # add reaction/cutaway after some shots
        if idx%4==3:
            # reaction shot
            rshot_type = "reaction"
            rcam = CAMERA_PRESETS.get(rshot_type)
            rdur = 0.7
            rshot = {
                "index": f"{idx}_r",
                "type": rshot_type,
                "camera": rcam,
                "duration_hint": rdur,
                "start_time": round(time_cursor,3),
                "end_time": round(time_cursor+rdur,3),
                "speaker": None,
                "text": "reaction_cutaway",
                "blocking": blocking,
                "lighting": lighting,
                "notes": "automatic reaction/cutaway"
            }
            shots.append(rshot)
            time_cursor += rdur
    # create a simple storyboard frames hints (textual thumbnails)
    frames = []
    for s in shots:
        focus = "characters" if s.get("blocking") else "environment"
        desc = f"{s['type']} - {s.get('speaker') or 'narration'} - focus:{focus}"
        frames.append({"shot_index": s["index"], "thumb_hint": desc, "focus_bbox": [0.3,0.2,0.4,0.6]})
    return {"ok": True, "scene_graph": scene_graph, "shot_list": shots, "storyboard_frames": frames, "total_duration": round(time_cursor,3)}
