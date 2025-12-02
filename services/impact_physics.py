# services/impact_physics.py
import math, json
from pathlib import Path

def impulse_from_force(force, mass=8.0):
    # simple: impulse velocity = force / mass (very simplified)
    return force / max(0.1, mass)

def compute_impacts(choreo):
    events = []
    for item in choreo.get("timeline", []):
        if item.get("force",0) > 0:
            vel = impulse_from_force(item["force"])
            events.append({
                "frame": item["start_frame"] + int(item["frames"]/2),
                "actor_hit": "B" if item["actor"]=="A" else "A",
                "force": item["force"],
                "impulse_vel": vel,
                "ragdoll_threshold": 40  # threshold above which ragdoll may trigger
            })
    return events

def needs_ragdoll(impact_event):
    return impact_event["force"] >= impact_event.get("ragdoll_threshold",40)
