# services/personality_blender.py
"""
Blend generic motion priors with personality weights.
Personality profiles change amplitude, frequency, head/arm bias.
"""

import math, json
from pathlib import Path

PERSONALITY_PRESETS = {
    "neutral": {"energy_mult":1.0, "arm_bias":0.5, "head_emph":0.5, "gesture_freq":1.0},
    "energetic": {"energy_mult":1.5, "arm_bias":0.8, "head_emph":0.8, "gesture_freq":1.3},
    "calm": {"energy_mult":0.6, "arm_bias":0.3, "head_emph":0.3, "gesture_freq":0.7},
    "formal": {"energy_mult":0.8, "arm_bias":0.2, "head_emph":0.4, "gesture_freq":0.6}
}

def apply_personality_to_motion(motion_frames: list, personality: str = "neutral"):
    p = PERSONALITY_PRESETS.get(personality, PERSONALITY_PRESETS["neutral"])
    out = []
    for f in motion_frames:
        m = dict(f)  # copy
        # scale shoulder / arm swings
        m["left_arm_swing"] = m.get("left_arm_swing",0.0) * p["energy_mult"] * p["arm_bias"]
        m["right_arm_swing"] = m.get("right_arm_swing",0.0) * p["energy_mult"] * (1.0 - p["arm_bias"] + 0.5)
        # head emphasis
        m["neck_tilt"] = m.get("neck_tilt",0.0) * (1.0 + p["head_emph"])
        # overall smoothing of energy peaks: reduce jaggies for calm
        if p["gesture_freq"] < 1.0:
            # simple low-pass: average with previous
            # later implement proper filter
            pass
        out.append(m)
    return out
