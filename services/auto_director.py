# services/auto_director.py
import os, json, uuid, subprocess, shlex
from pathlib import Path

ROOT = Path(".").resolve()
JOBDIR = ROOT / "jobs" / "director"
OUT = ROOT / "static" / "director"
BLENDER_SCRIPT = ROOT / "blender_scripts" / "camera_choreographer.py"
JOBDIR.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

DEFAULT_PRESETS = {
    "cinematic": {"cut_freq": "beat", "coverage":["wide","medium","close"], "lens": [35,50,85], "move_prob":0.6},
    "interview": {"cut_freq":"slow","coverage":["medium","close"], "lens":[50,85], "move_prob":0.2},
    "dynamic": {"cut_freq":"fast","coverage":["wide","medium","close","insert"], "lens":[24,35,50], "move_prob":0.9}
}

def create_director_job(scene_blend: str, timeline: dict, preset: str = "cinematic", out_prefix: str | None = None):
    """
    timeline: dict or list describing sequence:
      { "duration": 60.0,
        "beats": [{"t":0.5,"speaker":"A","emotion":"angry"}, ...]  OR simple segments [{"start":0,"end":3,"speaker":"A","action":"walk"}]
      }
    returns job_id + writes job json + spawns blender script (non-blocking)
    """
    tid = _tid()
    job = {"job_id": tid, "scene_blend": scene_blend, "timeline": timeline, "preset": DEFAULT_PRESETS.get(preset, DEFAULT_PRESETS['cinematic']), "out_prefix": out_prefix or str(OUT / f"job_{tid}_")}
    jf = JOBDIR / f"dir_{tid}.json"
    jf.write_text(json.dumps(job, indent=2))
    cmd = f"blender --background {shlex.quote(scene_blend)} --python {shlex.quote(str(BLENDER_SCRIPT))} -- {shlex.quote(str(jf))} {shlex.quote(job['out_prefix'])}"
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "task_id": tid, "job_file": str(jf), "pid": p.pid}
