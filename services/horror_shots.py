# services/horror_shots.py
SHOTS = {
  "low":[{"shot":"slow_pan","frames":80},{"shot":"wide_idle","frames":60}],
  "medium":[{"shot":"tight_door","frames":40},{"shot":"over_shoulder_shadow","frames":30},{"shot":"rack_focus","frames":30}],
  "high":[{"shot":"jump_close","frames":12},{"shot":"quick_cut_shock","frames":10},{"shot":"extreme_close_eye","frames":18},{"shot":"whip_pan","frames":8}]
}

def compose_shots(level):
    seq = SHOTS.get(level, SHOTS["low"])
    # add start frame fields
    cur = 1
    for s in seq:
        s["start"] = cur
        cur += s["frames"]
    return {"timeline": seq, "total_frames": cur-1}
