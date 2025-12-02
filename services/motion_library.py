# services/motion_library.py
import os, json
from pathlib import Path

ROOT = Path(".").resolve()
LIB_DIR = ROOT / "blender_scripts" / "motion_cycles"

DEFAULTS = {
    "walk": {"file":"walk_cycle.fbx", "frames":48, "loop":True, "root_motion":True},
    "run": {"file":"run_cycle.fbx", "frames":32, "loop":True, "root_motion":True},
    "jump": {"file":"jump_cycle.fbx", "frames":24, "loop":False, "root_motion":False},
    "punch": {"file":"punch_cycle.fbx", "frames":12, "loop":False, "root_motion":False},
    "dance": {"file":"dance_cycle.fbx", "frames":120, "loop":True, "root_motion":True}
}

def get_cycle(name):
    cfg = DEFAULTS.get(name)
    if not cfg:
        return None
    f = LIB_DIR / cfg['file']
    if not f.exists():
        return None
    return {"name": name, "path": str(f), **cfg}

def list_cycles():
    return [k for k in DEFAULTS.keys() if get_cycle(k) is not None]

def load_manifest():
    # quick manifest for availability
    m = {}
    for k in DEFAULTS.keys():
        c = get_cycle(k)
        m[k] = c
    return m
