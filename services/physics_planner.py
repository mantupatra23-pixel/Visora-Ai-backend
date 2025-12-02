# services/physics_planner.py
import math, json
from pathlib import Path
ROOT = Path(".").resolve()
PLANS = ROOT / "jobs" / "props" / "plans"
PLANS.mkdir(parents=True, exist_ok=True)

def plan_throw(from_loc, target_loc, speed=6.0, gravity=-9.81, arc_factor=1.0):
    """
    Simple ballistic trajectory planner (returns list of sample frames positions and times)
    Uses physics ballistic equation under gravity (2D approx).
    """
    dx = target_loc[0] - from_loc[0]
    dz = target_loc[2] - from_loc[2]
    dist = math.hypot(dx, target_loc[1] - from_loc[1])
    # time estimate
    t = dist / speed if speed>0.1 else 1.0
    samples = max(6, int(t*24))
    traj = []
    for i in range(samples+1):
        tt = (i/samples) * t
        # linear interp for horizontal
        x = from_loc[0] + (dx)*(i/samples)
        y = from_loc[1] + (target_loc[1]-from_loc[1])*(i/samples)
        # vertical ballistic with arc_factor
        # initial vertical velocity approximation:
        vz = (dz - 0.5*gravity*(t**2))/t
        z = from_loc[2] + vz*tt + 0.5*gravity*(tt**2)
        traj.append({"t": tt, "pos":[x,y,z]})
    return {"ok": True, "time": t, "samples": samples, "trajectory": traj}

def save_plan(job_id, plan):
    p = PLANS / f"{job_id}_plan.json"
    p.write_text(json.dumps(plan, indent=2))
    return str(p)
