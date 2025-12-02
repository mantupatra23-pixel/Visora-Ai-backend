# services/fight_planner.py
import json, uuid, time
from pathlib import Path

ROOT = Path(".").resolve()
JOBS = ROOT / "jobs" / "fight"
JOBS.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

# basic move library (extendable)
MOVE_LIBRARY = {
    "punch_right": {"duration_frames": 8, "delta":[0.2,0,0], "force": 30},
    "punch_left": {"duration_frames": 8, "delta":[-0.2,0,0], "force": 28},
    "kick_right": {"duration_frames": 10, "delta":[0.4,0,0], "force": 45},
    "dodge": {"duration_frames": 6, "delta":[0, -0.3,0], "force": 0},
    "block": {"duration_frames": 6, "delta":[0,0,0], "force": 0},
    "throw": {"duration_frames": 20, "delta":[0.6,0,0], "force": 60}
}

def build_choreography(script_line: str, length_sec:int=6, fps:int=24, aggressor="A", defender="B"):
    # naive heuristics: pick moves by keywords; else simple pattern
    words = script_line.lower()
    seq = []
    total_frames = length_sec * fps
    cur = 1
    # if 'punch' present favor punch sequence
    if "punch" in words or "hit" in words:
        plan = ["punch_right","punch_left","kick_right","dodge","punch_right"]
    elif "throw" in words or "toss" in words:
        plan = ["grab","throw"]
        # fallback if not in library
        plan = ["punch_right","throw"]
    elif "fight" in words or "chase" in words:
        plan = ["punch_right","kick_right","dodge","punch_left","throw"]
    else:
        plan = ["punch_right","punch_left","dodge","kick_right"]

    for m in plan:
        move = MOVE_LIBRARY.get(m, {"duration_frames":8,"delta":[0,0,0],"force":0})
        seq.append({
            "actor": aggressor if m not in ("dodge","block") else defender,
            "move": m,
            "start_frame": cur,
            "frames": move["duration_frames"],
            "force": move.get("force",0),
            "delta": move.get("delta",[0,0,0])
        })
        cur += move["duration_frames"]
        if cur > total_frames:
            break

    # remaining frames pad idle
    return {"job_id": f"fight_{_tid()}","created_at":time.time(), "length_sec": length_sec, "fps":fps, "timeline": seq, "aggressor":aggressor, "defender":defender, "output_path": str(JOBS / (f"fight_{_tid()}.json"))}

def save_job(job):
    p = Path(job.get("output_path"))
    p.write_text(json.dumps(job, indent=2))
    return str(p)
