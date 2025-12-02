# services/romantic_shot.py
ROMANTIC_SHOTS = {
    "light": [
        {"shot":"soft_wide","frames":40},
        {"shot":"gentle_closeup","frames":30}
    ],
    "medium":[
        {"shot":"close_face","frames":35},
        {"shot":"hands_touch","frames":20},
        {"shot":"camera_push","frames":25}
    ],
    "deep":[
        {"shot":"tear_closeup","frames":35},
        {"shot":"embrace_mid","frames":40},
        {"shot":"slow_circle","frames":45}
    ]
}

def compose_romantic(level, fps=24):
    seq = ROMANTIC_SHOTS.get(level, ROMANTIC_SHOTS["light"])
    for s in seq:
        s["frames"] = int(s["frames"])
    return seq
