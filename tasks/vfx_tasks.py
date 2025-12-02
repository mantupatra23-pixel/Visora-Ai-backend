# tasks/vfx_tasks.py
from celery import Celery
import os, shlex, subprocess, json
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
FFMPEG = os.getenv("FFMPEG","ffmpeg")
app = Celery('vfx', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def run_planar_key_and_vfx(self, jobfile):
    job = json.loads(Path(jobfile).read_text())
    outdir = Path(job.get("output_dir"))
    outdir.mkdir(parents=True, exist_ok=True)
    # 1) run planar tracker & key
    script = Path("blender_scripts") / "planar_tracker_keyer.py"
    cmd1 = f'{BLENDER_BIN} --background --python {script} -- "{jobfile}" "{outdir}"'
    p1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
    # 2) spawn particle VFX on impact frames if requested
    if job.get("options", {}).get("spawn_effects"):
        pv_script = Path("blender_scripts") / "particle_vfx.py"
        cmd2 = f'{BLENDER_BIN} --background --python {pv_script} -- "{jobfile}" "{outdir}"'
        p2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
    # 3) package result: compose overlays with ffmpeg if needed (simple)
    # check for compositor output files (Blender file output node produces files)
    # For now return logs
    return {"ok": True, "logs": {"planar": p1.stdout[:4000], "vfx": (p2.stdout[:4000] if job.get("options",{}).get("spawn_effects") else "")}}

@app.task(bind=True)
def run_plate_replace(self, plate_path, bg_video, dst_pts, src_pts, out_video):
    # compute homography and warp using OpenCV then ffmpeg overlay
    from services.plate_replace import compute_homography, warp_plate, ffmpeg_overlay
    import numpy as np
    H = compute_homography(src_pts, dst_pts)
    tmp_warp = str(Path(out_video).parent / ("warped_plate.png"))
    img = warp_plate(plate_path, H, tmp_warp, out_size=(1920,1080))
    ok, out, err = ffmpeg_overlay(bg_video, tmp_warp, out_video)
    return {"ok": ok, "ffmpeg_out": out, "ffmpeg_err": err}
