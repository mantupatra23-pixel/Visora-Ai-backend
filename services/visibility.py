# services/visibility.py
"""
Simple helpers & config for occlusion checks (used by Blender scripts).
This file is pure-Python helpers; actual raycasts run inside Blender (bpy).
"""
from pathlib import Path
import json
DEFAULT_PARAMS = {
    "samples": 9,
    "occlusion_threshold": 0.25,   # fraction of sample rays that can be occluded before rejecting camera pos
    "sample_radius": 0.15,         # meters around target center to sample rays
    "max_attempts": 12
}

def save_visibility_config(path: str):
    Path(path).write_text(json.dumps(DEFAULT_PARAMS, indent=2))

def load_visibility_config(path: str):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return DEFAULT_PARAMS
