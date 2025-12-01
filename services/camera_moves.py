# services/camera_moves.py
"""
High level definitions for moves: dolly_in, push_out, whip, arc, subtle_shake
Return parameters consumed by Blender spline generator.
"""
def move_params_for_shot(shot_type, intensity=1.0):
    if shot_type == "close":
        return {"type":"subtle_reframe","magnitude":0.02*intensity, "duration_factor":0.6}
    if shot_type == "medium":
        return {"type":"dolly_in","magnitude":0.3*intensity, "duration_factor":1.0}
    if shot_type == "wide":
        return {"type":"slow_pan","magnitude":0.15*intensity, "duration_factor":1.2}
    return {"type":"none","magnitude":0.0,"duration_factor":1.0}
