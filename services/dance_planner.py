# services/dance_planner.py
import json, uuid, time
from pathlib import Path

ROOT = Path(".").resolve()
JOBS = ROOT / "jobs" / "music"
JOBS.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

# small move bank — move names map to anim clips in AnimBank
MOVE_BANK = {
    "step_left": {"frames": 8, "clip":"step_left"},
    "step_right":{"frames":8,"clip":"step_right"},
    "spin":{"frames":16,"clip":"spin"},
    "pose":{"frames":12,"clip":"pose"},
    "jump":{"frames":10,"clip":"jump"},
    "slide":{"frames":12,"clip":"slide"},
    "body_wave":{"frames":14,"clip":"body_wave"}
}

def build_choreography_from_beats(beats, bpm=None, length_sec=None, dancers=["DancerA","DancerB"], style="pop"):
    """
    beats: list of beat times (seconds) OR None (if fallback, use bpm)
    returns job json with per-beat moves for dancers
    """
    job_id = f"music_{_tid()}"
    timeline = []
    # simple patterns: alternate on even/odd beats, include occasional spin/jump on strong beats
    for i, t in enumerate(beats or []):
        strong = (i % 4 == 0)
        dancer = dancers[i % len(dancers)]
        if strong:
            move = "spin" if (i % 8 == 0) else "jump"
        else:
            move = "step_left" if (i % 2==0) else "step_right"
        clip = MOVE_BANK.get(move, {}).get("clip", move)
        frames = MOVE_BANK.get(move, {}).get("frames", 8)
        timeline.append({"beat_index": i, "time": t, "dancer": dancer, "move": move, "clip": clip, "frames": frames})
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "bpm": bpm,
        "beats_count": len(beats or []),
        "dancers": dancers,
        "timeline": timeline,
        "output_path": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job
