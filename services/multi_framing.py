# services/multi_framing.py
"""
High-level framing utilities: compute target centroid, two-shot offsets, OTS anchor selection.
Returns framing descriptor used by Blender choreographer.
"""
from mathutils import Vector

def compute_centroid(objects):
    pts = [o.location for o in objects]
    if not pts: return Vector((0,0,0))
    s = Vector((0,0,0))
    for p in pts: s += p
    return s/len(pts)

def two_shot_positions(char_a_center, char_b_center, distance_factor=1.2):
    # place camera between A and B, offset slightly to create 3/4 view
    mid = (char_a_center + char_b_center) / 2.0
    direction = (char_a_center - char_b_center).normalized()
    # camera sits behind mid along direction's perpendicular (-Y) and slightly above
    cam_pos = mid + Vector((0.0, - (char_a_center - char_b_center).length * distance_factor, max(char_a_center.z, char_b_center.z) * 0.3))
    return {"mid": mid, "camera_pos": cam_pos}
