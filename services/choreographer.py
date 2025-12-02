# services/choreographer.py
import json, math
from pathlib import Path

def plan_multi_character(actions_per_char: dict, spacing=1.5):
    """
    actions_per_char: {"charA":[{action...}, ...], "charB":[...]}
    simple planner:
      - compute timeline per character
      - offset characters to avoid collisions using spacing along X axis
      - return plan with start_frame offsets
    """
    plan = {}
    timeline_len = 0
    for i, (char, acts) in enumerate(actions_per_char.items()):
        offset = i * spacing
        cur_frame = 1
        plan[char] = {"offset": offset, "actions": []}
        for a in acts:
            frames = a.get("frames", 30)
            plan[char]["actions"].append({"action": a['action'], "start_frame": cur_frame, "frames": frames})
            cur_frame += frames
        timeline_len = max(timeline_len, cur_frame)
    return {"plan": plan, "timeline_len": timeline_len}

def adjust_for_collisions(plan):
    # Basic: ensure characters with same world x do not overlap on same frame
    # For demo return plan as-is
    return plan
