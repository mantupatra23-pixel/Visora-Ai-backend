# services/mocap_retargeter.py
# Helper that records which anim clips (FBX) to retarget to which character.
import json, os
from pathlib import Path

def make_retarget_plan(anim_bank_dir, dancer_name, clips):
    """
    anim_bank_dir: folder with fbx clips named <clipname>.fbx
    clips: list of clip names to retarget in sequence with start frames
    returns: plan dict
    """
    plan = {"dancer": dancer_name, "clips": []}
    cur_frame = 1
    for c in clips:
        file = Path(anim_bank_dir) / (c + ".fbx")
        duration = 12  # default duration if unknown
        plan["clips"].append({"clip": c, "file": str(file), "start_frame": cur_frame, "frames": duration})
        cur_frame += duration
    return plan
