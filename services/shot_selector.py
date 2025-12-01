# services/shot_selector.py
"""
Hybrid shot selector:
- heuristic_selector(timeline) -> initial shot list
- ml_rescorer(shots, features) -> re-ranks/suggests changes (stub)
"""
import math, random

def heuristic_selector(timeline, preset):
    """
    timeline: {"duration":.., "beats":[{"t":..,"speaker":..,"emphasis":..},...]}
    preset influences desired cut frequency and coverage
    """
    shots = []
    duration = timeline.get("duration", 10.0)
    beats = sorted(timeline.get("beats",[]), key=lambda b: b.get("t",0))
    # start with master shot 0..first beat or first 2 seconds
    first_cut = beats[0]['t'] if beats else min(2.0, duration/4.0)
    shots.append({"start":0.0,"end":first_cut,"type":"master"})
    for i, b in enumerate(beats):
        t = b.get("t",0)
        next_t = beats[i+1].get("t") if i+1<len(beats) else min(duration, t+2.0)
        # if high emphasis, create close shot around beat
        if b.get("emphasis",0.0) > 0.6:
            shots.append({"start": max(0,t-0.2), "end": min(duration, t+0.8), "type":"close", "speaker": b.get("speaker")})
        else:
            # medium shot covering until next beat
            shots.append({"start": t, "end": next_t, "type":"medium", "speaker": b.get("speaker")})
    # merge overlapping and sort
    shots = sorted(shots, key=lambda s: s['start'])
    merged = []
    for s in shots:
        if not merged or s['start'] >= merged[-1]['end']:
            merged.append(s)
        else:
            # extend end if needed
            merged[-1]['end'] = max(merged[-1]['end'], s['end'])
    return merged

# ML rescorer stub: accept shots & frame-level features -> return possibly modified shots
def ml_rescorer(shots, features):
    """
    Stub: A real model could be a small transformer or classifier that scores shot quality.
    Here we apply small random improvements (simulate a model).
    """
    for s in shots:
        # tiny tweak: if speaker change and shot type is master, recommend medium
        if s.get("type")=="master" and s.get("speaker"):
            s['type'] = "medium"
    return shots
