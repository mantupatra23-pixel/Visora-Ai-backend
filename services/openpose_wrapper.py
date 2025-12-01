# services/openpose_wrapper.py
import os, subprocess, uuid, shlex
from pathlib import Path
ROOT = Path(".").resolve()
OUT = ROOT / "static" / "mocap_openpose"
OUT.mkdir(parents=True, exist_ok=True)

OPENPOSE_BIN = os.getenv("OPENPOSE_BIN", "/opt/openpose/build/examples/openpose/openpose")  # default inside docker

def _task_id():
    return uuid.uuid4().hex[:10]

def run_openpose_on_video(video_path: str, out_json_dir: str | None = None, body: int = 1, format="json"):
    """
    Runs OpenPose CLI to extract 2D keypoints and saves results to out_json_dir.
    Requires OpenPose built with --build_caffe and examples compiled.
    """
    tid = _task_id()
    out_dir = Path(out_json_dir or (OUT / tid))
    out_dir.mkdir(parents=True, exist_ok=True)
    # example options: --write_json <dir> --display 0 --render_pose 0 --model_pose BODY_25
    model_opt = "--model_pose BODY_25" if body==25 else "--model_pose COCO"
    cmd = f"{shlex.quote(OPENPOSE_BIN)} --video {shlex.quote(video_path)} --write_json {shlex.quote(str(out_dir))} --display 0 --render_pose 0 {model_opt}"
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
        return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "out_dir": str(out_dir)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
