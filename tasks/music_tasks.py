# tasks/music_tasks.py
from celery import Celery
import shlex, subprocess, json, os
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
FFMPEG = os.getenv("FFMPEG","ffmpeg")
app = Celery('music', broker=BROKER, backend=BROKER)

@app.task
def run_music_pipeline(audio_path, anim_bank_dir, dancers=["DancerA","DancerB"]):
    # 1) analyze beats
    from services.beat_analyzer import analyze_beats
    ba = analyze_beats(audio_path, use_librosa=True)
    if not ba.get("ok"):
        return {"ok": False, "error": "beat_analysis_failed", "detail": ba}
    beats = ba["beats"]
    bpm = ba["bpm"]
    # 2) build choreography
    from services.dance_planner import build_choreography_from_beats
    job = build_choreography_from_beats(beats, bpm, dancers=dancers)
    jobfile = Path("jobs/music") / (job["job_id"] + ".json")
    jobfile.write_text(json.dumps(job, indent=2))
    # 3) create stage lighting in Blender (stage_lighting)
    outdir = Path("jobs/music") / (job["job_id"] + "_out"); outdir.mkdir(parents=True, exist_ok=True)
    script = Path("blender_scripts") / "stage_lighting.py"
    cmd = f"{BLENDER_BIN} --background --python {script} -- {str(jobfile)} {str(outdir)}"
    subprocess.run(cmd, shell=True)
    # 4) retarget clips for each dancer (optional) - using mocap plan
    from services.mocap_retargeter import make_retarget_plan
    # naive: plan clips from timeline for each dancer
    dancers_plans = {}
    for d in dancers:
        clips = [t["clip"] for t in job["timeline"] if t["dancer"]==d]
        plan = make_retarget_plan(anim_bank_dir, d, clips)
        planf = outdir / f"{d}_plan.json"
        Path(planf).write_text(json.dumps(plan, indent=2))
        # run blender mocap baker for each (simple blocking call)
        mocap_script = Path("blender_scripts") / "mocap_baker.py"
        blender_cmd = f"{BLENDER_BIN} --background --python {mocap_script} -- {str(planf)} {str(outdir / (d + '_retargeted.blend'))}"
        subprocess.run(blender_cmd, shell=True)
    # 5) export edit (fcpxml) to align cuts to beats
    from services.sync_edit import build_cut_list_from_beats, export_fcpxml_from_cuts
    cuts = build_cut_list_from_beats(job)
    fcpxml = outdir / (job["job_id"] + "_edit.fcpxml")
    export_fcpxml_from_cuts(cuts, str(fcpxml))
    return {"ok": True, "job": str(jobfile), "outdir": str(outdir)}
