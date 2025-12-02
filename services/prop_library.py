# services/prop_library.py
from pathlib import Path
import json

ROOT = Path(".").resolve()
PROP_DIR = ROOT / "assets" / "props"
PROP_DIR.mkdir(parents=True, exist_ok=True)

# Simple manifest — keep FBX/GLB files in assets/props/
MANIFEST = {
    "sword": {"file":"sword.fbx","hand":"right","grip_style":"onehand","mass":2.0},
    "axe": {"file":"axe.fbx","hand":"right","grip_style":"twohand","mass":3.5},
    "phone": {"file":"phone.fbx","hand":"right","grip_style":"onehand","mass":0.2},
    "cup": {"file":"cup.fbx","hand":"left","grip_style":"onehand","mass":0.1},
    "laptop": {"file":"laptop.fbx","hand":"both","grip_style":"lap","mass":2.0}
}

def list_props():
    # augment file paths
    out = {}
    for k,v in MANIFEST.items():
        p = PROP_DIR / v['file']
        out[k] = {**v, "path": str(p), "exists": p.exists()}
    return out

def get_prop(name):
    return list_props().get(name)
