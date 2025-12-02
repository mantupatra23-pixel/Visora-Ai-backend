# services/mocap_advanced.py
import json, time, uuid
from pathlib import Path
from services.motion_library import get_cycle, list_cycles

JOBS = Path("jobs/mocap")
JOBS.mkdir(parents=True, exist_ok=True)

def _tid():
    return uuid.uuid4().hex[:8]

def build_advanced_job(script_text, rig="humanoid_mixamo", style="default", name=None, options=None):
    # parse and reuse existing parser
    from services.mocap_pro import parse_script
    actions = parse_script(script_text)
    # refine actions: if actions consecutive of same type -> merge with extended frames
    merged = []
    for a in actions:
        if merged and merged[-1]['action']==a['action']:
            merged[-1]['frames'] += a.get('frames',0)
        else:
            merged.append(a)
    # enhance with cycle quality: if a cycle exists, map it
    for a in merged:
        cyc = get_cycle(a['action'])
        if cyc:
            a['use_cycle'] = cyc['path']
            # adjust frames to cycle frames if loop
            if cyc.get('loop'):
                a['frames'] = cyc.get('frames', a['frames'])
    job_id = name or f"mocap_adv_{_tid()}"
    job = {"job_id": job_id, "created_at": time.time(), "rig": rig, "style": style, "actions": merged, "options": options or {}, "output_path": str(JOBS / (job_id + ".json"))}
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job
