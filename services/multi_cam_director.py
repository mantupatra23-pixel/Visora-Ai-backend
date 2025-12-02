# services/multi_cam_director.py
import json, uuid, time
from pathlib import Path

def build_multi_cam_plan(choreo_jobfile, camera_set=None):
    job = json.loads(Path(choreo_jobfile).read_text())
    timeline = job.get("timeline", [])
    cams = camera_set or ["wide","close","dolly","handheld"]
    # For each beat entry create camera coverage choices and preferred camera
    out_timeline = []
    cur_frame = 1
    for i, t in enumerate(timeline):
        duration_frames = t.get("frames", 8)
        # choose camera priority: strong beat -> close or dolly
        strong = (i % 4 == 0)
        pref = "dolly" if strong else ("close" if i%2==0 else "wide")
        cameras = [{"name":pref,"weight":0.8}] + [{"name":c,"weight":0.2} for c in cams if c!=pref]
        out_timeline.append({"beat_index": i, "start_frame": cur_frame, "frames": duration_frames, "cameras": cameras, "move": t.get("move")})
        cur_frame += duration_frames
    plan = {"job_id": job.get("job_id","mc_"+uuid.uuid4().hex[:6]), "timeline": out_timeline, "created_at": time.time()}
    out_path = Path("jobs/multicam") / (plan["job_id"] + ".json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2))
    return str(out_path)
