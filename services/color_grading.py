# services/color_grading.py
import os, json, time, uuid, subprocess
from pathlib import Path

ROOT = Path(".").resolve()
JOBS = ROOT / "jobs" / "grading"
JOBS.mkdir(parents=True, exist_ok=True)
PRESETS_FILE = ROOT / "assets" / "grading_presets.json"

def _tid(): return uuid.uuid4().hex[:8]

def load_presets():
    if PRESETS_FILE.exists():
        return json.loads(PRESETS_FILE.read_text())
    # fallback
    return {
        "teal_orange": {"name":"Teal & Orange","lut":"teal_orange.cube","skin_protect":True},
        "filmic": {"name":"Filmic","lut":"filmic.cube","skin_protect":True},
        "noir": {"name":"Noir B&W","lut":"noir.cube","skin_protect":False},
        "warm": {"name":"Warm Boost","lut":"warm.cube","skin_protect":True},
        "cold": {"name":"Cold Blue","lut":"cold.cube","skin_protect":True},
        "high_contrast": {"name":"High Contrast","lut":"hc.cube","skin_protect":True}
    }

def detect_mood_from_image(image_path: str):
    # lightweight heuristics: average color + brightness -> mood suggestion
    try:
        import cv2, numpy as np
        img = cv2.imread(str(image_path))
        if img is None: return {"ok": False, "error":"cannot_read"}
        avg = img.mean(axis=(0,1))  # BGR
        brightness = avg.mean()
        # simple rules
        if brightness < 80:
            mood = "noir"
        elif avg[2] > avg[0] + 10:  # more red (remember BGR)
            mood = "warm"
        elif avg[0] > avg[2] + 10:
            mood = "cold"
        else:
            mood = "filmic"
        return {"ok": True, "mood": mood, "avg": avg.tolist(), "brightness": float(brightness)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def build_job(input_path: str, preset: str | None = None, output_dir: str | None = None, protect_skin: bool = True):
    job_id = f"grade_{_tid()}"
    out = Path(output_dir or (JOBS / (job_id + "_out")))
    out.mkdir(parents=True, exist_ok=True)
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "input_path": str(input_path),
        "preset": preset,
        "output_dir": str(out),
        "protect_skin": protect_skin,
        "status": "queued",
        "output_path": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job

def apply_lut_with_ocio(input_img, output_img, lut_cube_path):
    """
    Try to use OpenColorIO CLI if installed: ociolutimage or ocio CLI.
    Fallback to OpenCV-based cube application (scripts/grade_images.py).
    """
    # first try ocio command line (if available)
    try:
        # ociolutimage is part of OpenColorIO tools if installed
        cmd = f"ociolutimage --lut=\"{lut_cube_path}\" \"{input_img}\" \"{output_img}\""
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            return {"ok": True, "method":"ocio_cli", "stdout": res.stdout}
    except Exception:
        pass
    # fallback: use grade_images.py apply_cube (python)
    cmd = f"python3 scripts/grade_images.py --input \"{input_img}\" --output \"{output_img}\" --cube \"{lut_cube_path}\""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"ok": res.returncode == 0, "method":"python_fallback", "stdout": res.stdout, "stderr": res.stderr}
