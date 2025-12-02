# services/edit_rules.py
import json, math, time, uuid
from pathlib import Path

def _tid(): return uuid.uuid4().hex[:8]

# Basic continuity/180° enforcement stub (for later ML upgrade)
def enforce_180_rule(shots):
    # placeholder: ensure alternating camera sides do not break 180 rule by adjusting camera roll/angles metadata
    # here we just annotate shots as '180_ok': True
    for s in shots:
        s['180_ok'] = True
    return shots

def choose_transitions(timeline):
    """
    timeline: [{"shot":name,"start":int,"frames":int,"cam":str, "type":...}, ...]
    returns same list augmented with 'transition' field (cut, dissolve, lcut)
    """
    out = []
    for i, item in enumerate(timeline):
        tr = "cut"
        if item.get('shot') in ('establishing','wide') and i>0:
            tr = "dissolve"
        # keep L-cuts near dialogue transitions (simple heuristic)
        if item.get('shot') in ('dialogue_two_shot','over_shoulder'):
            tr = "lcut"
        item['transition'] = tr
        out.append(item)
    return out

def build_edl(job_id, timeline, fps=24):
    """
    Build simple EDL (CMX3600-like) as a list of events with reel/source names and frame ranges.
    """
    entries = []
    event_num = 1
    for t in timeline:
        start = t['start_frame'] if 'start_frame' in t else t.get('start', t.get('start_frame',1))
        length = t.get('frames', t.get('duration_frames', 24))
        end = start + length - 1
        entries.append({
            "event": event_num,
            "reel": t.get('cam', t.get('shot', 'cam1')),
            "start": start,
            "end": end,
            "transition": t.get('transition','CUT'),
            "shot": t.get('shot')
        })
        event_num += 1
    return entries

def export_edl_to_file(edl_list, out_path):
    p = Path(out_path)
    lines = []
    lines.append("TITLE: Visora_EDL")
    for e in edl_list:
        lines.append(f"{e['event']:03d}  {e['reel']}  V     C        {e['start']:06d} {e['end']:06d}")
        # simplistic — not CMX3600 exact formatting but usable
    p.write_text("\n".join(lines))
    return str(p)

# convenience builder
def generate_edl_for_job(job_json_path, out_path):
    job = json.loads(Path(job_json_path).read_text())
    timeline = job.get('plan', {}).get('timeline', [])
    timeline = enforce_180_rule(timeline)
    timeline = choose_transitions(timeline)
    edl = build_edl(job.get('job_id','job'), timeline)
    return export_edl_to_file(edl, out_path)
