# tasks/color_tasks.py
from celery import Celery
import os, json, shlex, subprocess
from pathlib import Path
import time

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('grading', broker=BROKER, backend=BROKER)

# choose grader scripts (relative paths inside repo)
SKINPROTECT_SCRIPT = "scripts/grade_images_skinprotect.py"
DNN_PROTECT_SCRIPT = "scripts/grade_images_dnn.py"
FALLBACK_SCRIPT = "scripts/grade_images.py"

@app.task(bind=True)
def run_grading(self, jobfile_path):
    """
    jobfile expected JSON keys:
      - input_path: str (file or directory)
      - output_dir: str
      - preset: optional preset name (looks up assets/grading_presets.json)
      - lut_path: optional LUT path (file)
      - protect_skin: optional bool (default True) - prefer skin-protection graders
    """
    jobf = Path(jobfile_path)
    if not jobf.exists():
        return {"ok": False, "error":"jobfile_missing"}
    try:
        job = json.loads(jobf.read_text())
    except Exception as e:
        return {"ok": False, "error": "bad_jobfile", "detail": str(e)}

    inp = Path(job.get('input_path', ''))
    outdir = Path(job.get('output_dir', 'output'))  # fallback output
    outdir.mkdir(parents=True, exist_ok=True)

    preset = job.get('preset')
    # load presets if available
    presets = {}
    presets_path = Path("assets/grading_presets.json")
    if presets_path.exists():
        try:
            presets = json.loads(presets_path.read_text())
        except Exception:
            presets = {}

    preset_cfg = presets.get(preset) if preset else None
    lut_path = None
    if preset_cfg:
        lut_path = preset_cfg.get('lut')
    # allow explicit override
    if job.get('lut_path'):
        lut_path = job.get('lut_path')

    # make lut_path absolute if relative and exists under assets
    if lut_path and not Path(lut_path).exists():
        candidate = Path("assets") / lut_path
        if candidate.exists():
            lut_path = str(candidate)
        else:
            # if still missing, unset so grader won't fail
            lut_path = None

    # decide which grader script to run
    use_skinprotect = job.get('protect_skin', True)
    grader_script = FALLBACK_SCRIPT
    if use_skinprotect:
        if Path(DNN_PROTECT_SCRIPT).exists():
            grader_script = DNN_PROTECT_SCRIPT
        elif Path(SKINPROTECT_SCRIPT).exists():
            grader_script = SKINPROTECT_SCRIPT
        else:
            grader_script = FALLBACK_SCRIPT
    else:
        grader_script = FALLBACK_SCRIPT

    # Build command. Both file and folder inputs supported depending on script.
    cube_arg = f'--cube "{lut_path}"' if lut_path else ""
    # optional exposure/contrast parameters
    exposure = job.get('exposure', 1.0)
    contrast = job.get('contrast', 1.0)

    cmd = f'python3 {shlex.quote(grader_script)} --input "{shlex.quote(str(inp))}" --output "{shlex.quote(str(outdir))}" {cube_arg} --exposure {exposure} --contrast {contrast}'

    # update task state so frontend/monitor can see the command
    try:
        self.update_state(state="STARTED", meta={"cmd": cmd})
    except Exception:
        # ignore update errors in some celery setups
        pass

    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=7200)
        ok = p.returncode == 0
        result = {"ok": ok, "stdout": p.stdout[:8000], "stderr": p.stderr[:8000], "rc": p.returncode}
    except subprocess.TimeoutExpired as e:
        result = {"ok": False, "error": "timeout", "detail": str(e)}
    except Exception as e:
        result = {"ok": False, "error": "exec_error", "detail": str(e)}

    # write result manifest
    try:
        (outdir / "result.json").write_text(json.dumps(result, indent=2))
    except Exception:
        # if writing fails, return result anyway
        pass

    return result

