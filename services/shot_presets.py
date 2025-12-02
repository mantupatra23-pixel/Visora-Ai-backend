# services/shot_presets.py
from pathlib import Path
import json

ROOT = Path(".").resolve()
PRESET_FILE = ROOT / "assets" / "camera_presets.json"

DEFAULT_PRESETS = {
  "close_up": {"focal":85,"distance":1.0,"frame_coverage":"head","type":"closeup","notes":"Emotional detail"},
  "medium": {"focal":50,"distance":2.5,"type":"medium","notes":"Dialog coverage"},
  "wide": {"focal":24,"distance":8.0,"type":"wide","notes":"Establishing / environment"},
  "over_shoulder": {"focal":50,"distance":2.0,"type":"over_shoulder"},
  "dutch": {"focal":35,"distance":3.0,"tilt":15},
  "drone_orbit": {"focal":35,"altitude":8.0,"type":"drone","orbit_radius":6.0},
  "car_follow": {"focal":35,"distance":6.0,"type":"car_follow"}
}

def load_presets():
    if PRESET_FILE.exists():
        return json.loads(PRESET_FILE.read_text())
    return DEFAULT_PRESETS

def get_preset(name):
    return load_presets().get(name)
