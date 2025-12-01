# tasks/lip_orchestrator.py
from celery import Celery
import os
app = Celery('lip_orch', broker=os.getenv("CELERY_BROKER","redis://redis:6379/0"))

@app.task(bind=True)
def orchestrate_scene(self, package_json_path):
    """
    package_json contains:
      { "script_lines": [...], "characters":[{"name":"Boy","face":"path","voice":"v1","rig":"BoyArm"}], "scene_blend": "...", "out_prefix": "..." }
    Steps (simplified):
      1) generate multichar audio (services.multichar_dubbing.generate_tracks)
      2) for each segment produce per-character lip job (tasks.lip_tasks.run_lip_job.delay)
      3) wait for jobs / poll outputs (or use callbacks)
      4) produce combined timeline (ffmpeg concat) and return final path
    """
    import json, time
    from pathlib import Path
    from services.multichar_dubbing import generate_tracks
    from tasks.lip_tasks import run_lip_job
    pkg = json.load(open(package_json_path))
    # 1) generate tracks
    gen = generate_tracks(pkg.get("script_lines",[]), {c['name']: c.get("voice") for c in pkg.get("characters", [])})
    if not gen.get("ok"):
        return {"ok":False, "error":"dubbing_failed", "detail":gen}
    segments = gen.get("segments",[])
    # 2) enqueue per-segment lip jobs
    job_ids = []
    for seg in segments:
        speaker = seg['speaker']
        # find character config
        char = next((c for c in pkg.get("characters",[]) if c['name']==speaker), None)
        if not char:
            continue
        face = char.get("face")
        audio = seg['file']
        out_name = f"{speaker}_{uuid.uuid4().hex[:6]}.mp4"
        t = run_lip_job.delay(face, audio, None, "neutral", "sadtalker", out_name)
        job_ids.append({"speaker":speaker,"task_id":t.id,"expected_out":out_name})
    # 3) wait naive
    # NOTE: production should subscribe to task results; here simple polling
    results = []
    for j in job_ids:
        # poll
        for i in range(0, 600):
            res = run_lip_job.AsyncResult(j['task_id'])
            if res.ready():
                results.append(res.result)
                break
            time.sleep(1)
    # 4) collect produced mp4s and concat (simple)
    out_prefix = pkg.get("out_prefix") or "static/lip_orch/out_"
    # skipping concat code for brevity; return job summary
    return {"ok": True, "jobs": job_ids, "summary":"enqueue done - implement collector to await outputs"}
