# services/lift3d.py
import os, subprocess, uuid, shlex
from pathlib import Path
ROOT = Path(".").resolve()
OUT = ROOT / "static" / "mocap_3d"
OUT.mkdir(parents=True, exist_ok=True)

VIDEOPOSE_BIN = os.getenv("VIDEOPOSE_BIN", "/opt/videopose3d/run.py")  # assume you built a CLI wrapper

def _task_id():
    return uuid.uuid4().hex[:10]

def run_videopose3d(input_keypoints_json_dir: str, out_npz: str | None = None, model="resnet50"):
    tid = _task_id()
    out_npz = out_npz or str(OUT / f"vp3d_{tid}.npz")
    # This assumes you've prepared keypoints in the format VideoPose3D expects.
    cmd = f"python run_vidpose.py --input_dir {shlex.quote(input_keypoints_json_dir)} --output {shlex.quote(out_npz)} --checkpoint {shlex.quote(model)}"
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=7200)
        return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "out": out_npz}
    except Exception as e:
        return {"ok": False, "error": str(e)}
