# services/inertial_filter.py
"""
Apply simple inertial filtering to per-joint signals:
- exponential smoothing on positions/rotations
- velocity clamp to avoid sudden jumps
This improves visual realism before export to BVH/retarget.
"""

def exponential_smooth(frames: list, alpha: float = 0.25, keys: list | None = None):
    if not frames: return frames
    keys = keys or [k for k in frames[0].keys() if k!="t"]
    smoothed = []
    prev = {k: frames[0].get(k,0.0) for k in keys}
    for f in frames:
        nf = dict(f)
        for k in keys:
            v = f.get(k,0.0)
            prev[k] = alpha * v + (1-alpha)*prev[k]
            nf[k] = prev[k]
        smoothed.append(nf)
    return smoothed

def velocity_clamp(frames: list, max_deg_per_sec: float = 360.0, fps: float = 25.0, keys: list | None = None):
    if not frames: return frames
    dt = 1.0/fps
    keys = keys or [k for k in frames[0].keys() if k!="t"]
    clamped = [dict(frames[0])]
    prev = frames[0]
    for f in frames[1:]:
        nf = dict(f)
        for k in keys:
            dv = f.get(k,0.0) - prev.get(k,0.0)
            maxdv = max_deg_per_sec * dt
            if dv > maxdv: nf[k] = prev.get(k,0.0) + maxdv
            elif dv < -maxdv: nf[k] = prev.get(k,0.0) - maxdv
        clamped.append(nf)
        prev = nf
    return clamped
