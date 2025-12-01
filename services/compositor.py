# services/compositor.py
"""
Auto Compositor & Color Grade Engine
- Accepts: job JSON with input passes (paths), grade preset (LUT or built-in), denoise options, deliverable specs
- Runs: blender headless compositor OR a ffmpeg+imagemagick pipeline depending on inputs
- Outputs: final image sequence or video, and metadata

Job example:
{
  "job_id": "optional",
  "input_passes": {
     "beauty":"renders/beauty_####.exr",
     "diffuse":"renders/diffuse_####.exr",
     "specular":"renders/spec_####.exr",
     "normal":"renders/normal_####.exr",
     "depth":"renders/depth_####.exr"
  },
  "start_frame":1,
  "end_frame":120,
  "denoise": {"method":"openimageio"|"blender","strength":0.5},
  "grade": {"type":"lut","path":"grades/cinematic.cube"} OR {"type":"preset","name":"filmic_warm"},
  "output": {"type":"mp4","path":"static/output/final.mp4","fps":25,"codec":"libx264"}
}
"""
import os, json, uuid, subprocess, shlex
from pathlib import Path

ROOT = Path(".").resolve()
JOBDIR = ROOT / "jobs" / "compositor"
OUT = ROOT / "static" / "compositor"
BLENDER_SCRIPT = ROOT / "blender_scripts" / "composite_passes.py"
JOBDIR.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def submit_comp_job(job_spec: dict):
    tid = job_spec.get("job_id") or _tid()
    job_spec["job_id"] = tid
    jobfile = JOBDIR / f"comp_{tid}.json"
    jobfile.write_text(json.dumps(job_spec, indent=2), encoding="utf-8")
    # call blender headless compositor
    cmd = f"blender --background --python {shlex.quote(str(BLENDER_SCRIPT))} -- {shlex.quote(str(jobfile))} {shlex.quote(str(OUT))}"
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "task_id": tid, "job_file": str(jobfile), "pid": p.pid}

def grade_with_ffmpeg(lut_path: str, in_pattern: str, out_video: str, fps: int = 25, codec: str = "libx264", crf: int = 18):
    """
    Apply 3D LUT using ffmpeg (with lut3d filter) on image sequence -> mp4
    in_pattern: e.g., static/compositor/out_%04d.png or %04d.exr
    lut_path: .cube LUT path
    """
    out_dir = Path(out_video).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = f'ffmpeg -y -r {fps} -i {shlex.quote(in_pattern)} -vf lut3d=file={shlex.quote(lut_path)} -c:v {shlex.quote(codec)} -crf {crf} {shlex.quote(out_video)}'
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "cmd": cmd}
