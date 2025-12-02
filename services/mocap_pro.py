# services/mocap_pro.py
"""
Full-Body Mocap PRO+ core.
- parse_script(text) -> list of actions with params
- build_action_sequence(actions) -> job spec (frames, clips, transitions)
- export_to_blender_job(job, out_jobfile)
"""
import json, uuid, time
from pathlib import Path

ROOT = Path(".").resolve()
JOBS_DIR = ROOT / "jobs" / "mocap"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

def _tid():
    return uuid.uuid4().hex[:8]

# Very simple grammar parser (extendable). This converts lines into action tokens.
ACTION_KEYWORDS = {
    "walk": "walk",
    "run": "run",
    "jump": "jump",
    "punch": "punch",
    "kick": "kick",
    "dance": "dance",
    "sit": "sit",
    "stand": "stand",
    "fall": "fall",
    "turn": "turn"
}

def parse_script(text: str):
    """
    Input: free text script. Output: list of actions with rough params.
    Very lightweight: find keywords and apply default params.
    """
    actions = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # If multi-line, each line is one action, else look for keywords in sentence
    if len(lines) > 1:
        sources = lines
    else:
        sources = [text]
    for s in sources:
        s_low = s.lower()
        for kw, act in ACTION_KEYWORDS.items():
            if kw in s_low:
                # parse modifiers: speed, intensity, direction, count
                speed = 1.0
                intensity = 1.0
                if "fast" in s_low: speed = 1.6
                if "slow" in s_low: speed = 0.6
                if "hard" in s_low or "strong" in s_low: intensity = 1.4
                # frames estimate per action (rough)
                frames = {"walk":48,"run":32,"jump":24,"punch":12,"kick":14,"dance":120,"sit":30,"stand":30,"fall":60,"turn":20}.get(act, 30)
                actions.append({"action": act, "source_text": s, "speed": speed, "intensity": intensity, "frames": int(frames* (1.0/speed))})
                break
    # fallback: if nothing found, add idle with small motion
    if not actions:
        actions.append({"action":"idle", "frames":60, "speed":1.0, "intensity":0.4, "source_text": text})
    return actions

def build_job_from_actions(actions: list, rig: str="humanoid_mixamo", out_name: str | None = None):
    jid = out_name or f"mocap_{_tid()}"
    job = {
        "job_id": jid,
        "created_at": time.time(),
        "rig": rig,
        "actions": actions,
        "export_format": "fbx",
        "bake_options": {"bake_constraints": True, "clean_cycles": True},
        "output_path": str(JOBS_DIR / (jid + ".json"))
    }
    (JOBS_DIR / (jid + ".json")).write_text(json.dumps(job, indent=2))
    return job

def save_job(job: dict):
    p = Path(job.get("output_path") or (JOBS_DIR / (job['job_id'] + ".json")))
    p.write_text(json.dumps(job, indent=2))
    return str(p)
