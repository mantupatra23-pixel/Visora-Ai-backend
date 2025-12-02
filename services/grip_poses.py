# services/grip_poses.py
import json
from pathlib import Path
ROOT = Path(".").resolve()
GRIP_DIR = ROOT / "assets" / "grips"
GRIP_DIR.mkdir(parents=True, exist_ok=True)

# Example grip files: create one for sword_onehand.json etc.
# format:
# {
#   "name": "sword_onehand",
#   "attach_bone": "hand.R",
#   "finger_pose": {
#       "thumb.01.R": {"rot":[0.1,0.0,0.0],"loc":[0,0,0]},
#       ...
#   },
#   "offset": {"loc":[0,0,0],"rot":[0,0,0],"scale":1.0}
# }

def list_grips():
    files = list(GRIP_DIR.glob("*.json"))
    out = [p.stem for p in files]
    return out

def save_grip(name: str, payload: dict):
    p = GRIP_DIR / f"{name}.json"
    p.write_text(json.dumps(payload, indent=2))
    return str(p)

def load_grip(name: str):
    p = GRIP_DIR / f"{name}.json"
    if not p.exists(): raise FileNotFoundError(p)
    return json.loads(p.read_text())

# seed some example grips if not present
def seed_examples():
    s = GRIP_DIR / "sword_onehand.json"
    if not s.exists():
        s.write_text(json.dumps({
            "name":"sword_onehand",
            "attach_bone":"hand.R",
            "offset":{"loc":[0.0,0.0,0.0],"rot":[0.0,0.0,0.0],"scale":1.0},
            "finger_pose":{}
        }, indent=2))
seed_examples()
